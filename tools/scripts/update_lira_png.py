import json
import base64
import struct
import zlib

def update_character_png(png_path, character_json_path):
    """Update PNG with character card data - properly handles ST format."""
    
    # Read PNG
    with open(png_path, 'rb') as f:
        png_data = f.read()
    
    # Read character JSON
    with open(character_json_path, 'r', encoding='utf-8') as f:
        char_data = f.read()
    
    # Parse PNG chunks
    chunks = []
    pos = 8  # Skip PNG signature
    
    while pos < len(png_data):
        length = struct.unpack('>I', png_data[pos:pos+4])[0]
        chunk_type = png_data[pos+4:pos+8].decode('ascii')
        chunk_data = png_data[pos+8:pos+8+length]
        crc = struct.unpack('>I', png_data[pos+8+length:pos+12+length])[0]
        
        # Skip existing chara/ccv3 chunks
        if chunk_type == 'tEXt':
            keyword = chunk_data.split(b'\x00')[0].decode('latin-1')
            if keyword in ('chara', 'ccv3'):
                pos += 12 + length
                continue
        
        chunks.append((chunk_type, chunk_data))
        pos += 12 + length
    
    # Create new tEXt chunks
    def make_text_chunk(keyword, text):
        raw = keyword.encode('latin-1') + b'\x00' + text.encode('utf-8')
        return ('tEXt', raw)
    
    # v2 chara chunk
    base64_v2 = base64.b64encode(char_data.encode('utf-8')).decode('ascii')
    chara_chunk = make_text_chunk('chara', base64_v2)
    
    # v3 ccv3 chunk
    v3_data = json.loads(char_data)
    v3_data['spec'] = 'chara_card_v3'
    v3_data['spec_version'] = '3.0'
    v3_json = json.dumps(v3_data, ensure_ascii=False)
    base64_v3 = base64.b64encode(v3_json.encode('utf-8')).decode('ascii')
    ccv3_chunk = make_text_chunk('ccv3', base64_v3)
    
    # Build new PNG
    result = bytearray(b'\x89PNG\r\n\x1a\n')
    
    for chunk_type, chunk_data in chunks:
        if chunk_type == 'IEND':
            # Insert our chunks before IEND
            for keyword, raw in [chara_chunk, ccv3_chunk]:
                data_bytes = raw
                type_bytes = chunk_type.encode('ascii') if keyword == 'IEND' else b'tEXt'
                # Wait, I'm mixing things up. Let me fix this.
                pass
            pass
    
    # Simpler approach: rebuild properly
    result = bytearray(b'\x89PNG\r\n\x1a\n')
    
    for chunk_type, chunk_data in chunks:
        if chunk_type == 'IEND':
            # Insert chara/ccv3 before IEND
            for new_type, new_data in [chara_chunk, ccv3_chunk]:
                type_bytes = new_type.encode('ascii')
                length = len(new_data)
                crc = zlib.crc32(type_bytes + new_data) & 0xffffffff
                result.extend(struct.pack('>I', length))
                result.extend(type_bytes)
                result.extend(new_data)
                result.extend(struct.pack('>I', crc))
        
        type_bytes = chunk_type.encode('ascii')
        length = len(chunk_data)
        crc = zlib.crc32(type_bytes + chunk_data) & 0xffffffff
        result.extend(struct.pack('>I', length))
        result.extend(type_bytes)
        result.extend(chunk_data)
        result.extend(struct.pack('>I', crc))
    
    with open(png_path, 'wb') as f:
        f.write(result)
    
    print(f"Updated {png_path}")
    print(f"  JSON size: {len(char_data)} chars")
    print(f"  PNG size: {len(result)} bytes")

if __name__ == '__main__':
    png_path = r"C:\Users\Mike Brooks\Documents\SillyTavern\data\default-user\characters\Lira.png"
    json_path = r"C:\Users\Mike Brooks\Documents\SillyTavern\data\default-user\characters\Lira.json"
    update_character_png(png_path, json_path)
