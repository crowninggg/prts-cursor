import AppKit
import Foundation

let resources = URL(fileURLWithPath: CommandLine.arguments[1])
var decoded = 0
for name in ["PRTS-Final-Static.cape", "PRTS-Final-Animated.cape"] {
    let raw = try Data(contentsOf: resources.appendingPathComponent(name))
    let cape = try PropertyListSerialization.propertyList(from: raw, options: [], format: nil) as! [String: Any]
    let cursors = cape["Cursors"] as! [String: [String: Any]]
    precondition(cursors.count == 40)
    for (_, value) in cursors {
        let frames = (value["FrameCount"] as! NSNumber).intValue
        let hotspot = NSPoint(x: (value["HotSpotX"] as! NSNumber).doubleValue,
                              y: (value["HotSpotY"] as! NSNumber).doubleValue)
        for raw in value["Representations"] as! [Data] {
            try autoreleasepool {
                guard let representation = NSBitmapImageRep(data: raw), let strip = representation.cgImage else {
                    throw NSError(domain: "PRTS", code: 1)
                }
                let width = representation.pixelsWide
                precondition(representation.pixelsHigh == width * frames)
                for index in 0..<frames {
                    let rect = CGRect(x: 0, y: index * width, width: width, height: width)
                    guard let frame = strip.cropping(to: rect) else { throw NSError(domain: "PRTS", code: 2) }
                    let image = NSImage(cgImage: frame, size: NSSize(width: 32, height: 32))
                    let cursor = NSCursor(image: image, hotSpot: hotspot)
                    precondition(cursor.image.size.width == 32 && cursor.hotSpot == hotspot)
                    decoded += 1
                }
            }
        }
    }
}
print("PASS AppKit decoded and constructed \(decoded) cursor frames from both 40-role themes.")
