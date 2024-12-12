#!/usr/bin/env python3

import re
import sys
import qrcode
import argparse
from dataclasses import dataclass
from typing import Optional

@dataclass
class RAMPNode:
    layer: str
    protocol: str
    params: Optional[str] = None
    meta: Optional[str] = None

class RAMPProcessor:
    PATTERNS = {
        'SYNTAX': r'^([A-Z])\/([A-Z])(:[^#]+)?(#.+)?$',
        'MAC': r'^([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})$',
        'FREQUENCY': r'^\d+\.\d{3}[MG]Hz$',
        'EXTENSION': r'^\d{4}$'
    }

    COLORS = {
        'physical': '#1a73e8',
        'network': '#34a853',
        'service': '#ea4335',
        'meta': '#fbbc04'
    }

    def parse(self, ramp_string: str) -> Optional[RAMPNode]:
        match = re.match(self.PATTERNS['SYNTAX'], ramp_string.upper())
        return None if not match else RAMPNode(
            layer=match.group(1),
            protocol=match.group(2),
            params=match.group(3)[1:] if match.group(3) else None,
            meta=match.group(4)[1:] if match.group(4) else None
        )

    def to_mermaid(self, node: RAMPNode) -> str:
        return "\n".join([
            "graph TB",
            f"    PHY[{node.layer}/{node.protocol}]",
            f"    PAR[{node.params or 'No Parameters'}]",
            f"    META[{node.meta or 'No Metadata'}]",
            "    PHY --> PAR",
            "    PAR --> META",
            "",
            "    style PHY fill:#1a73e8,color:white",
            "    style PAR fill:#34a853,color:white",
            "    style META fill:#ea4335,color:white"
        ])

    def to_qr(self, node: RAMPNode, filename: str) -> None:
        qr = qrcode.QRCode(version=1, box_size=10, border=5)
        ramp_uri = f"ramp://{node.layer}/{node.protocol}"
        if node.params:
            ramp_uri += f":{node.params}"
        if node.meta:
            ramp_uri += f"#{node.meta}"
        qr.add_data(ramp_uri)
        qr.make(fit=True)
        qr.make_image(fill_color="black", back_color="white").save(filename)

def main():
    parser = argparse.ArgumentParser(description='RAMP Protocol Parser & Visualizer')
    parser.add_argument('ramp', help='RAMP string (e.g., L/M:868#HIKING-01)')
    parser.add_argument('-o', '--output', help='Output file prefix for generated files')
    parser.add_argument('-m', '--mermaid', action='store_true', help='Generate Mermaid diagram')
    parser.add_argument('-q', '--qr', action='store_true', help='Generate QR code')
    args = parser.parse_args()

    processor = RAMPProcessor()
    node = processor.parse(args.ramp)
    
    if not node:
        sys.exit("Invalid RAMP string")

    prefix = args.output or f"ramp_{node.protocol.lower()}"
    
    if args.mermaid:
        with open(f"{prefix}.md", 'w') as f:
            f.write(processor.to_mermaid(node))
    
    if args.qr:
        processor.to_qr(node, f"{prefix}.png")

if __name__ == "__main__":
    main()
