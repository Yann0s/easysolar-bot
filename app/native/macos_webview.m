// Fenêtre macOS native (WKWebView) qui affiche l'interface servie en local ; repris de Pulsefy.
#import <Cocoa/Cocoa.h>
#import <WebKit/WebKit.h>

@interface EasySolarAppDelegate : NSObject <NSApplicationDelegate>
@property (strong, nonatomic) NSWindow *window;
@property (strong, nonatomic) WKWebView *webView;
@property (copy, nonatomic) NSString *initialUrl;
@end

@implementation EasySolarAppDelegate

- (void)setupMenuBar {
    NSMenu *menubar = [[NSMenu alloc] init];
    NSMenuItem *appMenuItem = [[NSMenuItem alloc] init];
    [menubar addItem:appMenuItem];
    [NSApp setMainMenu:menubar];
    NSMenu *appMenu = [[NSMenu alloc] initWithTitle:@"EasySolar"];
    [appMenu addItemWithTitle:@"Quitter EasySolar" action:@selector(terminate:) keyEquivalent:@"q"];
    [appMenuItem setSubmenu:appMenu];

    NSMenuItem *editMenuItem = [[NSMenuItem alloc] init];
    [menubar addItem:editMenuItem];
    NSMenu *editMenu = [[NSMenu alloc] initWithTitle:@"Édition"];
    [editMenu addItemWithTitle:@"Couper" action:@selector(cut:) keyEquivalent:@"x"];
    [editMenu addItemWithTitle:@"Copier" action:@selector(copy:) keyEquivalent:@"c"];
    [editMenu addItemWithTitle:@"Coller" action:@selector(paste:) keyEquivalent:@"v"];
    [editMenu addItemWithTitle:@"Tout sélectionner" action:@selector(selectAll:) keyEquivalent:@"a"];
    [editMenuItem setSubmenu:editMenu];
}

- (void)applicationDidFinishLaunching:(NSNotification *)notification {
    [self setupMenuBar];
    NSWindowStyleMask style = NSWindowStyleMaskTitled | NSWindowStyleMaskClosable |
                              NSWindowStyleMaskMiniaturizable | NSWindowStyleMaskResizable;
    self.window = [[NSWindow alloc] initWithContentRect:NSMakeRect(0, 0, 900, 700)
                                              styleMask:style
                                                backing:NSBackingStoreBuffered
                                                  defer:NO];
    [self.window setTitle:@"EasySolar 1600"];
    [self.window setMinSize:NSMakeSize(480, 400)];
    [self.window center];

    self.webView = [[WKWebView alloc] initWithFrame:[[self.window contentView] bounds]
                                      configuration:[[WKWebViewConfiguration alloc] init]];
    [self.webView setAutoresizingMask:(NSViewWidthSizable | NSViewHeightSizable)];
    [[self.window contentView] addSubview:self.webView];
    [self.webView loadRequest:[NSURLRequest requestWithURL:[NSURL URLWithString:self.initialUrl]]];

    [self.window makeKeyAndOrderFront:nil];
    [NSApp activateIgnoringOtherApps:YES];
}

- (BOOL)applicationShouldTerminateAfterLastWindowClosed:(NSApplication *)sender {
    return YES;
}

@end

void run_macos_webview(const char *url_cstr) {
    @autoreleasepool {
        NSApplication *app = [NSApplication sharedApplication];
        [app setActivationPolicy:NSApplicationActivationPolicyRegular];
        EasySolarAppDelegate *delegate = [[EasySolarAppDelegate alloc] init];
        delegate.initialUrl = [NSString stringWithUTF8String:url_cstr];
        [app setDelegate:delegate];
        [app run];
    }
}
