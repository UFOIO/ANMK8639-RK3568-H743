import sys
sys.stdout.reconfigure(encoding='utf-8')
filepath = r'C:\Users\gjt\Desktop\ANMK8639-RK3568-H743\rk3568_app\modules\web_ui.py'
with open(filepath, 'r', encoding='utf-8') as f:
    lines = f.readlines()

in_section = False
for i, line in enumerate(lines):
    s = line.strip()
    if '/api/config' in s:
        in_section = True
        for j in range(i-2, min(i+50, len(lines))):
            print(f'{j+1}: {lines[j].rstrip()[:250]}')
        print('---')
