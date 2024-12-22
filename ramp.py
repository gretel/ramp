#!/usr/bin/env python3

import re
import sys
import math
import argparse
from dataclasses import dataclass
from typing import Optional, List, Dict, Any
from pathlib import Path

@dataclass
class RAMPNode:
    """Core RAMP protocol data structure"""
    is_person: bool
    layer: str
    protocol: str
    params: Optional[str] = None
    meta: Optional[str] = None

    def to_uri(self) -> str:
        """Convert node to RAMP URI format"""
        base = f"{'~' if self.is_person else ''}{self.layer}/{self.protocol}"
        if self.params:
            base += f":{self.params}"
        if self.meta:
            base += f"#{self.meta}"
        return base

class RAMPDescriptor:
    """Protocol-specific parameter descriptions and formatting"""
    
    # Protocol descriptors
    PROTOCOLS = {
       'P': {  # Physical Layer
           'L': {'name': 'LoRa', 'icon': '📡', 
                 'format': lambda p: {'freq': f"{p[0]} MHz", 'spread': p[1], 'bw': f"{p[2]} kHz", 'rate': f"4/{p[3]}"}},
           'R': {'name': 'Radio', 'icon': '📻',
                 'format': lambda p: {'freq': p[0], 'mode': p[1]}},
           'W': {'name': 'WiFi', 'icon': '📶',
                 'format': lambda p: {'ch': p[0], 'bw': f"{p[1]} MHz"}},
           'B': {'name': 'BLE', 'icon': '🦷',
                 'format': lambda p: {'mac': p[0], 'type': p[1]}},
           'Z': {'name': 'Zigbee', 'icon': '🕸️',
                 'format': lambda p: {'ch': p[0], 'pan': p[1]}}
       },
       'N': {  # Network Layer
           'A': {'name': 'AS', 'icon': '🌐',
                 'format': lambda p: {'asn': p[0], 'prefix': p[1]}},
           'I': {'name': 'IPv4', 'icon': '🌐',
                 'format': lambda p: {'net': p[0], 'mask': p[1]}},
           '6': {'name': 'IPv6', 'icon': '🌐',
                 'format': lambda p: {'net': p[0], 'prefix': p[1]}},
           'O': {'name': 'Tor', 'icon': '🧅', 'needs_qr': True,
                 'format': lambda p: {'onion': p[0], 'port': p[1], 'type': p[2] if len(p)>2 else 'HS'}}
       },
       'A': {  # Application Layer
           'M': {'name': 'Matrix', 'icon': '💬', 'needs_qr': True,
                 'format': lambda p: {'user': p[0], 'room': p[1]}},
           'I': {'name': 'IRC', 'icon': '💬', 'needs_qr': True,
                 'format': lambda p: {'srv': p[0], 'ch': p[1]}},
           'H': {'name': 'HTTP', 'icon': '🌐', 'needs_qr': True,
                 'format': lambda p: {'host': p[0], 'path': p[1]}},
           'G': {'name': 'Gemini', 'icon': '🚀', 'needs_qr': True,
                 'format': lambda p: {'host': p[0], 'path': p[1]}}
       }
    }

    @classmethod
    def get_info(cls, node: RAMPNode) -> Dict[str, Any]:
        """Get formatted information for a RAMP node"""
        layer = cls.PROTOCOLS.get(node.layer, {})
        proto = layer.get(node.protocol, {})
        if not proto:
            return {}
            
        params = node.params.split('/') if node.params else []
        try:
            formatted = proto['format'](params)
            return {
                'name': proto['name'],
                'icon': proto.get('icon', '❓'),
                'params': formatted,
                'description': proto.get('description', ''),
                'needs_qr': proto.get('needs_qr', False)
            }
        except:
            return {}

class RAMPFormatter:
    """Format RAMP nodes as human-readable output"""
    
    def format(self, node: RAMPNode) -> str:
        """Format node as descriptive text"""
        info = RAMPDescriptor.get_info(node)
        if not info:
            return node.to_uri()
            
        lines = [f"{info['name']} ({info['description']})"]
        lines.extend(f"{k}: {v}" for k, v in info['params'].items())
        if node.meta:
            lines.append(f"ID: {node.meta}")
            
        return "\n".join(lines)

    def format_ascii(self, node: RAMPNode) -> str:
        """Format node as ASCII art label"""
        info = RAMPDescriptor.get_info(node)
        if not info:
            return node.to_uri()
            
        lines = [
            f"{info['icon']} {info['name']}",
            *[f"{k}: {v}" for k, v in info['params'].items()],
        ]
        if node.meta:
            lines.append(f"ID: {node.meta}")

        width = max(len(line) for line in lines) + 4
        border = "┌" + "─" * width + "┐"
        footer = "└" + "─" * width + "┘"
        
        result = [border]
        for line in lines:
            padding = " " * ((width - len(line)) // 2)
            result.append(f"│{padding}{line}{padding}│")
        result.append(footer)
        
        return "\n".join(result)

class RAMPValidator:
    """Validate RAMP protocol strings"""
    
    # Validation patterns
    PATTERNS = {
       'SYNTAX': r'^(~)?([A-Z])\/([A-Z])(:[^#]+)?(#.+)?$',
       'MAC': r'^([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})$',
       'FREQ': r'^\d+\.\d{3}[MG]Hz$',
       'CHAN': r'^\d{1,3}$',
       'MASK': r'^\d{1,2}$',  # CIDR notation
       'PORT': r'^\d{1,5}$',
       'ONION': r'^[a-z2-7]{56}\.onion$',
       'ASN': r'^\d{1,10}$',
       'USER': r'^@?[a-zA-Z0-9_.-]+$',
       'PATH': r'^/[a-zA-Z0-9/_.-]*$',
       'HOST': r'^[a-zA-Z0-9.-]+$'
    }

    def validate(self, ramp_string: str) -> Optional[RAMPNode]:
        """Validate and parse RAMP string into node"""
        match = re.match(self.PATTERNS['SYNTAX'], ramp_string.upper())
        if not match:
            return None
            
        node = RAMPNode(
            is_person=bool(match.group(1)),
            layer=match.group(2),
            protocol=match.group(3),
            params=match.group(4)[1:] if match.group(4) else None,
            meta=match.group(5)[1:] if match.group(5) else None
        )

        return node if self._validate_params(node) else None

    def _validate_params(self, node: RAMPNode) -> bool:
       if not node.params:
           return True
           
       try:
           p = node.params.split('/')
           if node.layer == 'P':
               if node.protocol == 'L':
                   return all([
                       re.match(r'^\d+\.\d{3}$', p[0]),  # freq
                       p[1] in map(str, range(7, 13)),   # spread
                       p[2] in ['125', '250', '500'],    # bandwidth
                       p[3] in map(str, range(5, 9))     # rate
                   ])
               if node.protocol == 'B':
                   return bool(re.match(self.PATTERNS['MAC'], p[0]))
               if node.protocol in ['W', 'Z']:
                   return bool(re.match(self.PATTERNS['CHAN'], p[0]))
                   
           elif node.layer == 'N':
               if node.protocol == 'A':
                   return bool(re.match(self.PATTERNS['ASN'], p[0]))
               if node.protocol in ['I', '6']:
                   return bool(re.match(self.PATTERNS['MASK'], p[1]))
               if node.protocol == 'O':
                   return bool(re.match(self.PATTERNS['ONION'], p[0]))
                   
           elif node.layer == 'A':
               if node.protocol == 'M':
                   return bool(re.match(self.PATTERNS['USER'], p[0]))
               if node.protocol in ['H', 'G']:
                   return bool(re.match(self.PATTERNS['HOST'], p[0]))
           
           return True
       except:
           return False

def main():
    parser = argparse.ArgumentParser(description='RAMP Protocol Parser & Formatter')
    parser.add_argument('ramp', help='RAMP string (e.g., P/L:868.100/7/125/5#NODE01)')
    parser.add_argument('--ascii', action='store_true', help='ASCII art output')
    args = parser.parse_args()

    validator = RAMPValidator()
    node = validator.validate(args.ramp)
    
    if not node:
        sys.exit("Invalid RAMP string")

    formatter = RAMPFormatter()
    if args.ascii:
        print(formatter.format_ascii(node))
    else:
        print(formatter.format(node))

if __name__ == "__main__":
    main()
