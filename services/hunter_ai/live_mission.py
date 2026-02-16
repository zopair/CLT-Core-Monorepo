
import os
import requests
from groq import Groq

# المحرك الأساسي
client = Groq(api_key=os.getenv('GROQ_API_KEY'))
headers = {"Authorization": f"token {os.getenv('GITHUB_TOKEN')}"}

def hunt_and_commit():
    print("🎯 Searching for REAL issues...")
    # البحث عن قضايا حقيقية محتاجة حلول برمجية في بايثون
    query = "language:python label:\"help wanted\" state:open"
    url = f"https://api.github.com/search/issues?q={query}&sort=created"
    
    res = requests.get(url, headers=headers).json()
    issues = res.get('items', [])

    if not issues:
        print("📭 No new issues found at this moment. Retrying later.")
        return

    target = issues[0] # البدء بأحدث قضية
    repo_url = target['repository_url']
    issue_title = target['title']
    
    print(f"🔥 Targeting Issue: {issue_title} in {repo_url}")

    # تحليل المهمة ووضع السعر (فوق 50$)
    analysis = client.chat.completions.create(
        messages=[{"role": "user", "content": f"Analyze this issue and provide a fix and price (min $50): {issue_title}"}],
        model="llama3-70b-8192"
    ).choices[0].message.content

    # رسالة الـ PR النهائية (سيتم وضعها كـ Comment أو PR)
    final_offer = f"""
👑 **Official Fix Proposal from Al-Zubair Tec Investment**

We have analyzed your issue: '{issue_title}'
Proposed Fix: [Included in this PR/Comment]

📊 **Evaluation & Quote:**
{analysis}

🛡️ **Golden Guarantee:** Refundable with 10% fee if not matching requirements.

💰 **Payment:** Binance UID `717654739`
"""
    # إرسال الكومنت كخطوة أولى للاشتباك
    comment_url = f"{target['url']}/comments"
    requests.post(comment_url, json={"body": final_offer}, headers=headers)
    print(f"✅ Real Offer Sent to: {target['html_url']}")

if __name__ == "__main__":
    hunt_and_commit()
