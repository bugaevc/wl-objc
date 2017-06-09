#include "wayland.h"

#import <Foundation/Foundation.h>
#import "wl-objc.h"

int main() {
    NSAutoreleasePool *pool = [NSAutoreleasePool new];

    WLDisplay *display = [WLDisplay connect];
    WLRegistry *registry = [display registry];

    __block WLCompositor *compositor;
    __block WLShm *shm;
    __block WLShell *shell;

    [registry setGlobalHandler:
        ^(uint32_t name, NSString *interface, uint32_t version) {
            if ([interface isEqualToString: @"wl_compositor"]) {
                compositor = [registry bind: [WLCompositor class]
                                    name: name
                                    version: 3];
            } else if ([interface isEqualToString: @"wl_shm"]) {
                shm = [registry bind: [WLShm class] name: name version: 1];
            } else if  ([interface isEqualToString: @"wl_shell"]) {
                shm = [registry bind: [WLShell class] name: name version: 1];
            }
    }];

    [display roundtrip];

    int width = 200;
    int height = 200;
    int stride = width * 4;
    int size = stride * height;

    int fd = syscall(SYS_memfd_create, "buffer", 0);
    ftruncate(fd, size);

    WLShmPool *pool = [shm createPoolWithFd: fd size: size];
    WLBuffer *buffer = [pool createBufferWithOffset: 0
                            width: width
                            height: height
                            stride: stride
                            format: WL_SHM_FORMAT_XRGB8888];

    WLSurface *surface = [compositor createSurface];
    WLShellSurface *shellSurface = [shell shellSurface: surface];
    [shellSurface setToplevel];
    [shellSurface setPingHandler: ^(int serial) {
        [shellSurface pongWithSerial: serial];
    }];

    [surface attachBuffer: buffer x: 0 y: 0];
    [surface commit];

    while (1) {
        [display dispatch];
        // TODO: break
    }

    // TODO: dispose of everything
    [display disconnect];
    [pool release];
}
