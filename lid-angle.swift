import Foundation
import IOKit.hid

let noOptions = IOOptionBits(kIOHIDOptionsTypeNone)

func findLidAngleDevice() -> IOHIDDevice? {
    let manager = IOHIDManagerCreate(kCFAllocatorDefault, noOptions)
    guard IOHIDManagerOpen(manager, noOptions) == kIOReturnSuccess else { return nil }
    defer { IOHIDManagerClose(manager, noOptions) }

    let matching: [String: Any] = [
        kIOHIDVendorIDKey as String: 0x05AC,
        kIOHIDProductIDKey as String: 0x8104,
        "UsagePage": 0x0020,
        "Usage": 0x008A,
    ]

    IOHIDManagerSetDeviceMatching(manager, matching as CFDictionary)

    guard let devices = IOHIDManagerCopyDevices(manager) as? Set<IOHIDDevice>,
          !devices.isEmpty else {
        return nil
    }

    for device in devices {
        guard IOHIDDeviceOpen(device, noOptions) == kIOReturnSuccess else { continue }

        var report = [UInt8](repeating: 0, count: 8)
        var length = CFIndex(report.count)

        let result = IOHIDDeviceGetReport(device, kIOHIDReportTypeFeature, 1, &report, &length)
        if result == kIOReturnSuccess, length >= 3 {
            IOHIDDeviceClose(device, noOptions)
            return device
        }
        IOHIDDeviceClose(device, noOptions)
    }

    return nil
}

func readAngle(device: IOHIDDevice) -> Int? {
    guard IOHIDDeviceOpen(device, noOptions) == kIOReturnSuccess else { return nil }
    defer { IOHIDDeviceClose(device, noOptions) }

    var report = [UInt8](repeating: 0, count: 8)
    var length = CFIndex(report.count)

    let result = IOHIDDeviceGetReport(device, kIOHIDReportTypeFeature, 1, &report, &length)
    guard result == kIOReturnSuccess, length >= 3 else { return nil }

    let raw = UInt16(report[2]) << 8 | UInt16(report[1])
    return Int(raw)
}

guard let device = findLidAngleDevice() else {
    fputs("no_sensor\n", stderr)
    print("-1")
    exit(1)
}

if let angle = readAngle(device: device) {
    print(angle)
} else {
    print("-1")
    exit(1)
}
