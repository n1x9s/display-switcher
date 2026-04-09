import Foundation
import CoreGraphics

let handle = dlopen("/System/Library/PrivateFrameworks/DisplayServices.framework/DisplayServices", RTLD_NOW)
guard handle != nil else {
    print("-1")
    exit(1)
}

typealias GetBrightnessFunc = @convention(c) (CGDirectDisplayID, UnsafeMutablePointer<Float>) -> Int32
let getBrightness = unsafeBitCast(dlsym(handle!, "DisplayServicesGetBrightness"), to: GetBrightnessFunc.self)

let maxDisplays: UInt32 = 8
var displays = [CGDirectDisplayID](repeating: 0, count: Int(maxDisplays))
var displayCount: UInt32 = 0
CGGetActiveDisplayList(maxDisplays, &displays, &displayCount)

for i in 0..<Int(displayCount) {
    if CGDisplayIsBuiltin(displays[i]) != 0 {
        var brightness: Float = -1
        let _ = getBrightness(displays[i], &brightness)
        print(String(format: "%.6f", brightness))
        dlclose(handle)
        exit(0)
    }
}

dlclose(handle!)
print("-1")
exit(1)
