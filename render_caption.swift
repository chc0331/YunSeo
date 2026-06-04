import AppKit
import Foundation

guard CommandLine.arguments.count >= 3 else {
    fputs("usage: render_caption.swift <output.png> <text>\n", stderr)
    exit(1)
}

let output = URL(fileURLWithPath: CommandLine.arguments[1])
let text = CommandLine.arguments[2]
let width = 1920
let height = 260
let paddingX: CGFloat = 36
let paddingY: CGFloat = 20
let cornerRadius: CGFloat = 22

let rep = NSBitmapImageRep(
    bitmapDataPlanes: nil,
    pixelsWide: width,
    pixelsHigh: height,
    bitsPerSample: 8,
    samplesPerPixel: 4,
    hasAlpha: true,
    isPlanar: false,
    colorSpaceName: .deviceRGB,
    bytesPerRow: 0,
    bitsPerPixel: 0
)!

NSGraphicsContext.saveGraphicsState()
NSGraphicsContext.current = NSGraphicsContext(bitmapImageRep: rep)

NSColor.clear.setFill()
NSRect(x: 0, y: 0, width: width, height: height).fill()

let paragraph = NSMutableParagraphStyle()
paragraph.alignment = .center

let shadow = NSShadow()
shadow.shadowColor = NSColor(calibratedWhite: 0.0, alpha: 0.35)
shadow.shadowBlurRadius = 6
shadow.shadowOffset = NSSize(width: 0, height: -2)

let font = NSFont(name: "AppleGothic", size: 54) ?? NSFont.systemFont(ofSize: 54, weight: .medium)
let attributes: [NSAttributedString.Key: Any] = [
    .font: font,
    .foregroundColor: NSColor.white,
    .paragraphStyle: paragraph,
    .shadow: shadow,
]

let attributed = NSAttributedString(string: text, attributes: attributes)
let textRect = attributed.boundingRect(
    with: NSSize(width: CGFloat(width) - 280, height: CGFloat(height)),
    options: [.usesLineFragmentOrigin, .usesFontLeading]
).integral

let boxWidth = textRect.width + paddingX * 2
let boxHeight = textRect.height + paddingY * 2
let boxRect = NSRect(
    x: (CGFloat(width) - boxWidth) / 2,
    y: (CGFloat(height) - boxHeight) / 2,
    width: boxWidth,
    height: boxHeight
)

NSColor(calibratedWhite: 0.0, alpha: 0.24).setFill()
NSBezierPath(roundedRect: boxRect, xRadius: cornerRadius, yRadius: cornerRadius).fill()

let drawRect = NSRect(
    x: boxRect.minX + paddingX,
    y: boxRect.minY + paddingY - 2,
    width: textRect.width,
    height: textRect.height
)
attributed.draw(with: drawRect, options: [.usesLineFragmentOrigin, .usesFontLeading])

NSGraphicsContext.restoreGraphicsState()

guard let png = rep.representation(using: .png, properties: [:]) else {
    fputs("failed to encode png\n", stderr)
    exit(2)
}

try png.write(to: output)
