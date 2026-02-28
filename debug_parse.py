from pathlib import Path
from pywiki.parsers.java import JavaParser

parser = JavaParser()
file_path = Path('D:/opensource/ruoyi-vue-pro-master-jdk17/yudao-framework/yudao-common/src/main/java/cn/iocoder/yudao/framework/common/enums/CommonStatusEnum.java')

content = file_path.read_text(encoding='utf-8')
tree = parser._parser.parse(bytes(content, 'utf-8'))
root = tree.root_node

def find_enum(node):
    if node.type == 'enum_declaration':
        print("=== Parsing enum_declaration ===")
        for child in node.children:
            text = child.text
            if isinstance(text, bytes):
                text = text.decode('utf-8')
            print(f"  {child.type}: {repr(text)[:60]}")
            
            if child.type == 'identifier':
                print(f"  ** Found identifier: {repr(text)}")
    for child in node.children:
        find_enum(child)

find_enum(root)

# Now test the actual parsing
print("\n=== Testing parser.parse_file ===")
result = parser.parse_file(file_path)
for module in result.modules:
    print(f"Module: {module.name}")
    for cls in module.classes:
        print(f"  Class name: {repr(cls.name)}")
        print(f"  Full name: {repr(cls.full_name)}")
