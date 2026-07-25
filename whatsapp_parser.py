import re
import json
import csv

def parse_whatsapp_export(file_path):
    """Parses a WhatsApp exported .txt chat file into structured data."""
    
    # Matches lines like: [25/07, 8:49 am] Shankar Anna: message text
    pattern = re.compile(
        r'^\[(\d{1,2}/\d{1,2}(?:/\d{2,4})?),\s*(\d{1,2}:\d{2}\s*[ap]m)\]\s*([^:]+):\s*(.*)$',
        re.IGNORECASE
    )

    messages = []

    with open(file_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue

            match = pattern.match(line)
            if match:
                date, time, sender, text = match.groups()
                messages.append({
                    'date': date,
                    'time': time,
                    'sender': sender.strip(),
                    'message': text.strip(),
                    'type': 'media' if '<Media omitted>' in text else 'text'
                })
            else:
                # This line is a continuation of the previous message (multi-line text)
                if messages:
                    messages[-1]['message'] += '\n' + line

    return messages


def save_as_json(messages, output_path):
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(messages, f, indent=2, ensure_ascii=False)


def save_as_csv(messages, output_path):
    with open(output_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=['date', 'time', 'sender', 'message', 'type'])
        writer.writeheader()
        writer.writerows(messages)


if __name__ == '__main__':
    messages = parse_whatsapp_export('chat_export.txt')
    save_as_json(messages, 'structured_chat.json')
    save_as_csv(messages, 'structured_chat.csv')
    print(f"Parsed {len(messages)} messages successfully.")