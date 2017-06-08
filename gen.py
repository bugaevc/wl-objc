#! /usr/bin/python3

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
                interface = Interface.parse(child)
                res.interfaces.append(interface)
        return res
        
    def print(self):
        print_comment(self.name + ' protocol')
        if self.copyright:
            print_comment(self.copyright, multiline=True)
        for interface in self.interfaces:
            interface.print()
            print()

class Interface:
    def parse(node):
        assert(node.tag == 'interface')
        res = Interface()
        res.name = node.attrib['name']
        res.version = node.attrib['version']
        res.requests = []
        res.events = []
        for child in node:
            if child.tag == 'description':
                res.description = child.text
            if child.tag == 'request':
                request = Request.parse(child)
                res.requests.append(request)
            if child.tag == 'event':
                event = Event.parse(child)
                res.events.append(event)
        return res
    
    def objc_name(name):
        if isinstance(name, Interface):
            name = name.name
        res = objc_case(name, first_capital=True)
        for prefix in 'wl', 'xdg', 'zxdg':
            if res.lower().startswith(prefix):
                l = len(prefix)
                res = prefix.upper() + res[l:]
        return res
        
    def print(self):
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

class Request:
    def parse(node):
        assert(node.tag == 'request')
        res = Request()
        res.name = node.attrib['name']
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
        res.objc_args = deepcopy(res.args)
        for arg in res.objc_args:
            arg.name = objc_case(arg.name)
            if arg.type == 'object':
                arg.type = Interface.objc_name(arg.interface) + ' *'
            elif arg.type == 'string':
                arg.type = 'NSString *'
            elif arg.type == 'uint':
                arg.type = 'uint32_t'
            else:
                # TODO: other types
                pass
        if res.args:
            a0n = objc_case(res.args[0].name, first_capital=True)
            if not res.objc_name.endswith(a0n):
                res.objc_name += 'With' + a0n
        return res
        
    def print_decl(self):
        if self.description:
            print_comment(self.description, multiline=True)
        return_type = 'void'
        if self.new_id is not None:
            return_type = Interface.objc_name(self.new_id.interface) + ' *'
        print('- ({})'.format(return_type), end='')
        if not self.objc_args:
            print(' {};'.format(self.objc_name))
        else:
            print(end=' ')
            self.objc_args[0].print(label=self.objc_name)
            for arg in self.objc_args[1:]:
                print(end=' ')
                arg.print()
            print(';')


class Event:
    def parse(node):
        assert(node.tag == 'event')
        res = Event()
        res.name = node.attrib['name']
        res.args = []
        for child in node:
            if child.tag == 'description':
                res.description = child.text
            if child.tag == 'arg':
                arg = Arg.parse(child)
                res.args.append(arg)
        return res
        
    def print_decl(self):
        if self.description:
            print_comment(self.description, multiline=True)
        print('- (TODO)', objc_case(self.name))

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
    
    def print(self, label=None):
        if label is None:
            label = self.name
        print('{}: ({}) {}'.format(label, self.type, self.name), end='')
        

print_comment('Automatically generated by wl-objc bindings generator')
tree = ET.parse('/dev/stdin')
root = tree.getroot()
Protocol.parse(root).print()

