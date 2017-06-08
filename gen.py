#! /usr/bin/python3

import sys
import xml.etree.ElementTree as ET
from copy import deepcopy

def print_comment(s, multiline=False):
    if not multiline:
        print('/*', s.strip(), '*/')
        return
    print('/*')
    for line in s.splitlines():
        print(' *', line.strip())
    print(' */')

def objc_case(name, first_capital=False):
    res = name.replace('_', ' ').title().replace(' ', '')
    if not first_capital:
        res = res[0].lower() + res[1:]
    return res

class Protocol:
    def parse(node):
        assert(node.tag == 'protocol')
        res = Protocol()
        res.name = node.attrib['name']
        res.interfaces = []
        for child in node:
            if child.tag == 'copyright':
                res.copyright = child.text
            if child.tag == 'interface':
                interface = Interface.parse(child, protocol=res)
                res.interfaces.append(interface)
        return res

    def print_decl(self):
        print_comment(self.name + ' protocol')
        if self.copyright:
            print_comment(self.copyright, multiline=True)
        for interface in self.interfaces:
            interface.print_decl()
            print()

    def print_impl(self):
        for interface in self.interfaces:
            interface.print_impl()
            print()

class Interface:
    def parse(node, protocol):
        assert(node.tag == 'interface')
        res = Interface()
        res.name = node.attrib['name']
        res.protocol = protocol
        res.version = node.attrib['version']
        res.requests = []
        res.events = []
        for child in node:
            if child.tag == 'description':
                res.description = child.text
            if child.tag == 'request':
                request = Request.parse(child, interface=res)
                res.requests.append(request)
            if child.tag == 'event':
                event = Event.parse(child, interface=res)
                res.events.append(event)
        if res.name == 'wl_display':
            res.requests += [
                res.gen_connect(),
                res.gen_connect_with_name(),
                res.gen_connect_to_fd(),
                res.gen_disconnect(),
            ]
        return res

    def gen_connect(self):
        r = Request()
        r.name = 'connect'
        r.static = True
        r.description = None
        r.interface = self
        r.objc_name = 'connect'
        r.args = []
        r.objc_args = []
        r.new_id = Arg()
        r.new_id.type = 'interface'
        r.new_id.interface = 'wl_display'
        return r
    def gen_connect_with_name(self):
        r = Request()
        r.name = 'connect'
        r.static = True
        r.description = None
        r.interface = self
        r.objc_name = 'connectWithName'
        r.args = [Arg()]
        r.objc_args = [Arg()]
        r.args[0].name = 'name'
        r.args[0].type = 'string'
        r.objc_args[0].name = 'name'
        r.objc_args[0].type = 'NSString *'
        r.new_id = Arg()
        r.new_id.type = 'interface'
        r.new_id.interface = 'wl_display'
        return r
    def gen_connect_to_fd(self):
        r = Request()
        r.name = 'connect'
        r.static = True
        r.description = None
        r.interface = self
        r.objc_name = 'connectToFd'
        r.args = [Arg()]
        r.objc_args = [Arg()]
        r.args[0].name = 'fd'
        r.args[0].type = 'fd'
        r.objc_args[0].name = 'fd'
        r.objc_args[0].type = 'int'
        r.new_id = Arg()
        r.new_id.type = 'interface'
        r.new_id.interface = 'wl_display'
        return r
    def gen_disconnect(self):
        r = Request()
        r.name = 'disconnect'
        r.static = False
        r.description = None
        r.interface = self
        r.objc_name = 'disconnect'
        r.args = []
        r.objc_args = []
        r.new_id = None
        return r

    def objc_name(name):
        if isinstance(name, Interface):
            name = name.name
        res = objc_case(name, first_capital=True)
        for prefix in 'wl', 'wp', 'xdg', 'zxdg':
            if res.lower().startswith(prefix):
                l = len(prefix)
                res = prefix.upper() + res[l:]
        return res

    def print_decl(self):
        if self.description:
            print_comment(self.description, multiline=True)
        print('@interface', self.objc_name(), '{')
        print('struct', self.name, '*rawHandle;')
        print('}')
        for request in self.requests:
            request.print_decl()
        for event in self.events:
            event.print_decl()
        print('@end')

    def print_impl(self):
        print('@implementation', self.objc_name(), '{')
        for event in self.events:
            event.print_block_handler_decl()
        print('}')
        for request in self.requests:
            request.print_impl()
        for event in self.events:
            event.print_impl()
            event.print_handler()
        print('- (void) setupHandlers {')
        for event in self.events:
            print(objc_case(event.name) + 'BlockHandler = nil;')
        print('static const struct {}_listener listener ='.format(self.name), '{')
        print(',\n'.join(
            '.{} = {}_{}_c_handler'.format(event.name, self.name, event.name)
            for event in self.events
        ))
        print('};')
        print(self.name + '_add_listener(rawHandle, &listener, self);')
        print('}')
        print('@end')

class Request:
    def parse(node, interface):
        assert(node.tag == 'request')
        res = Request()
        res.name = node.attrib['name']
        res.interface = interface
        res.static = False
        res.args = []
        for child in node:
            if child.tag == 'description':
                res.description = child.text
            if child.tag == 'arg':
                arg = Arg.parse(child)
                res.args.append(arg)
        # generate objc names and args
        if not res.name.startswith('get'):
            res.objc_name = objc_case(res.name)
        else:
            res.objc_name = objc_case(res.name[3:])
        if not res.args:
            res.new_id = None
            res.objc_args = []
            return res
        if res.args[0].type == 'new_id':
            res.new_id = res.args[0]
            res.args = res.args[1:]
        else:
            res.new_id = None
        res.objc_args = [arg.objcify() for arg in res.args]
        if res.args:
            a0n = objc_case(res.args[0].name, first_capital=True)
            if not res.objc_name.endswith(a0n):
                res.objc_name += 'With' + a0n
        return res

    def print_header(self):
        return_type = 'void'
        if self.new_id is not None:
            return_type = Interface.objc_name(self.new_id.interface) + ' *'
        print('{} ({})'.format('+' if self.static else '-', return_type), end='')
        if not self.objc_args:
            print(' ' + self.objc_name, end='')
        else:
            print(end=' ')
            self.objc_args[0].print_decl(label=self.objc_name)
            for arg in self.objc_args[1:]:
                print(end=' ')
                arg.print_decl()

    def print_decl(self):
        if self.description:
            print_comment(self.description, multiline=True)
        self.print_header()
        print(';')

    def print_impl(self):
        self.print_header()
        print(' {')
        this = Arg()
        this.name = 'rawHandle'
        this.type = 'id'
        args = ', '.join(arg.to_c() for arg in [this] + self.objc_args)
        if self.new_id is not None:
            return_type = Interface.objc_name(self.new_id.interface)
            print('{t} *res = [{t} alloc];'.format(t=return_type))
            print('res->rawHandle = ', end='')
        print('{}_{}({});'.format(self.interface.name, self.name, args))
        if self.new_id is not None:
            print('[res setupHandlers];')
            print('return res;')
        print('}')


class Event:
    def parse(node, interface):
        assert(node.tag == 'event')
        res = Event()
        res.name = node.attrib['name']
        res.interface = interface
        res.args = []
        for child in node:
            if child.tag == 'description':
                res.description = child.text
            if child.tag == 'arg':
                arg = Arg.parse(child)
                res.args.append(arg)
        return res

    def print_header(self):
        name = objc_case('set_{}_handler'.format(self.name))
        args_decl = ', '.join(arg.objcify().cdecl() for arg in self.args)
        print('- (void) {}: (void (^)({})) handler'.format(name, args_decl), end='')

    def print_block_handler_decl(self):
        handler = objc_case(self.name) + 'BlockHandler'
        args_decl = ', '.join(arg.objcify().cdecl() for arg in self.args)
        print('void (^{})({}));'.format(handler, args_decl))

    def print_decl(self):
        if self.description:
            print_comment(self.description, multiline=True)
        self.print_header()
        print(';')

    def print_impl(self):
        self.print_header()
        print(' {')
        handler = objc_case(self.name) + 'BlockHandler'
        print('[{} release];'.format(handler))
        print('{} = [handler copy];'.format(handler))
        print('}')

    def print_handler(self):
        handler = objc_case(self.name) + 'BlockHandler'
        print('static void {}_{}_c_handler'.format(self.interface.name, self.name), end='(')
        void_data = Arg()
        void_data.name = 'data'
        void_data.type = 'void *'
        this = Arg()
        this.name = 'th'
        this.type = self.interface.name + ' *'
        print(', '.join(arg.cdecl() for arg in [void_data, this] + self.args), end=') {\n')
        print(self.interface.objc_name() + ' *me = data;')
        print('if (me->{} == nil) return;'.format(handler))
        args = ', '.join(arg.to_obj_c() for arg in self.args)
        print('me->{}({});'.format(handler, args))
        print('}')

class Arg:
    def parse(node):
        assert(node.tag == 'arg')
        res = Arg()
        res.name = node.attrib['name']
        res.type = node.attrib['type']
        res.summary = node.attrib['summary']
        if 'interface' in node.attrib:
            res.interface = node.attrib['interface']
            res.allow_null = False
        if 'allow-null' in node.attrib:
            res.allow_null = node.attrib['allow-null'] == 'true'
        return res

    def objcify(self):
        res = Arg()
        res.name = objc_case(self.name)
        res.summary = self.summary
        if self.type == 'object':
            if hasattr(self, 'interface'):
                res.type = Interface.objc_name(self.interface) + ' *'
            else:
                res.type = 'id'
        elif self.type == 'string':
            res.type = 'NSString *'
        elif self.type == 'uint':
            res.type = 'uint32_t'
        elif self.type == 'fd':
            res.type = 'int'
        else:
            # TODO: other types
            res.type = self.type
        return res

    def print_decl(self, label=None):
        if label is None:
            label = self.name
        print('{}: ({}) {}'.format(label, self.type, self.name), end='')

    def cdecl(self):
        tp = self.type
        if tp == 'string':
            tp = 'const char *'
        elif tp == 'object':
            tp = 'void *'
        return '{} {}'.format(tp, self.name)

    def to_c(self):
        if self.type == 'NSString *':
            return '[{} UTF8String]'.format(self.name)
        elif self.type.endswith('*'):
            return self.name + '->rawHandle'
        else:
            return self.name

    def to_obj_c(self):
        if self.type == 'string':
            return '[NSString initWithUTF8String: {}]'.format(self.name)
        return self.name


print_comment('Automatically generated by wl-objc bindings generator')
tree = ET.parse('/dev/stdin')

root = tree.getroot()
protocol = Protocol.parse(root)

def usage():
    print('''Usage:
    {argv0} header < some_wayland_protocol.xml > some_wayland_protocol.h
    {argv0} code   < some_wayland_protocol.xml > some_wayland_protocol.c
    '''.format(argv0=sys.argv[0]), file=sys.stderr)

if len(sys.argv) != 2:
    usage()
elif sys.argv[1] == 'header':
    protocol.print_decl()
elif sys.argv[1] == 'code':
    protocol.print_impl()
else:
    usage()
