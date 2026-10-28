# Check web_app.py structure
src = open(r'C:\Users\diorl\.cline\data\workspaces\chat\agent-1c-demo\agent\web_app.py', encoding='utf-8').read()
print('Total:', len(src))
print('do_GET:', 'do_GET' in src)
print('do_POST:', 'do_POST' in src)
print('class Handler:', 'class Handler' in src)
