"""Static content: campaign templates, micro-learning lessons and the quiz bank.

All organisations, people and domains here are fictional ("Halvard & Co.",
halvard.co). Simulation links point back at this app's own landing page.
"""

TEMPLATES = {
    "text": [
        {
            "id": "text-reset", "title": "Urgent security password reset", "difficulty": "Medium",
            "sender": "IT Security <security-alert@halvard-co-verify.com>",
            "subject": "CRITICAL: Account suspended in 2 hours",
            "body": "Dear user,\nOur servers detected unauthorized login attempts. Reset your corporate credentials immediately or access will be revoked.\nHalvard IT Security",
            "cta": "Reset credentials now",
            "flags": [
                {"match": "halvard-co-verify.com", "note": "Look-alike sender domain. The real company domain is halvard.co."},
                {"match": "2 hours", "note": "Artificial deadline designed to rush you."},
                {"match": "access will be revoked", "note": "Threat of loss to override caution."},
                {"match": "Dear user", "note": "Generic greeting. Internal IT knows your name."},
            ],
        },
        {
            "id": "text-wire", "title": "CFO wire transfer request", "difficulty": "Hard",
            "sender": "Diane Keller (CFO) <d.keller.office@gmail.com>",
            "subject": "Urgent: quick wire payment needed for client",
            "body": "I am currently in a meeting with vendors and can't take calls. Please process this $14,200 wire transfer right now and keep this confidential. PDF attached.\nSent from my iPhone",
            "cta": "Open Payment_Details.pdf",
            "flags": [
                {"match": "gmail.com", "note": "An executive writing from a personal account."},
                {"match": "can't take calls", "note": "Blocks you from verifying by phone."},
                {"match": "$14,200", "note": "Payment that skips the approval workflow."},
                {"match": "keep this confidential", "note": "Secrecy isolates you from colleagues who would spot it."},
            ],
        },
    ],
    "image": [
        {
            "id": "image-qr", "title": "Overdue invoice with QR code", "difficulty": "Medium", "image": "qr-invoice",
            "sender": "Accounts Receivable <billing@canva-invoices.net>",
            "subject": "Invoice #88294 OVERDUE - immediate action required",
            "body": "Please scan the QR code in the attached image to verify payment details on our encrypted payment gateway. Late fees apply after 24 hours.",
            "flags": [
                {"match": "canva-invoices.net", "note": "A vendor name bolted onto an unrelated domain."},
                {"match": "scan the QR code", "note": "QR codes hide the destination and move you to an unmanaged phone."},
                {"match": "24 hours", "note": "Late-fee deadline adds pressure."},
            ],
        },
        {
            "id": "image-quota", "title": "Spoofed mailbox-full screenshot", "difficulty": "Hard", "image": "quota",
            "sender": "Mailbox Admin <no-reply@mail-quota-center.com>",
            "subject": "M365 storage full: incoming mail will bounce",
            "body": "Your mailbox exceeded its 99 GB limit. See the attached status and expand your quota before emails are bounced.",
            "cta": "Expand quota",
            "flags": [
                {"match": "mail-quota-center.com", "note": "Not a Microsoft or Halvard domain."},
                {"match": "attached status", "note": "The 'status panel' is just a picture, so its button can go anywhere."},
                {"match": "before emails are bounced", "note": "Fear of missing mail used as leverage."},
            ],
        },
    ],
    "url": [
        {
            "id": "url-typo", "title": "Typosquatted Office365 portal", "difficulty": "Hard",
            "sender": "Microsoft 365 <no-reply@micros0ft-verify.com>",
            "subject": "Action required: update your security questions",
            "body": "We are updating account security for all staff. Confirm your security questions to keep access to mail and files.",
            "cta": "Click here to update your security questions",
            "display_link": "https://login.micros0ft-verify.com/auth/login",
            "flags": [
                {"match": "micros0ft", "note": "A zero replaces the letter o. Read domains character by character."},
                {"match": "for all staff", "note": "Mass 'policy' framing to seem routine."},
                {"match": "keep access", "note": "Threat of losing access."},
            ],
        },
        {
            "id": "url-ip", "title": "IP-based salary spreadsheet share", "difficulty": "Easy",
            "sender": "SharePoint <share@halvard-docs.com>",
            "subject": "Q3 salary adjustment matrix shared with you",
            "body": "HR shared a file with you: Q3-Salaries.xlsx. This link expires in 48 hours.",
            "cta": "View Q3 Salary Adjustment Matrix",
            "display_link": "http://192.168.45.102/docs/sharepoint/Q3-Salaries.xlsx",
            "flags": [
                {"match": "halvard-docs.com", "note": "File shares come from the real SharePoint domain, not a look-alike."},
                {"match": "Q3-Salaries", "note": "Salary data is irresistible bait, and HR wouldn't share it widely."},
                {"match": "48 hours", "note": "Expiry pressure."},
            ],
        },
    ],
    "audio": [
        {
            "id": "audio-ceo", "title": "AI voice clone: CEO emergency request", "difficulty": "Hard",
            "caller": "+44 7700 900418 (\"Martin - CEO mobile\")", "speaker": "Executive AI synthesis",
            "script": "Hey, this is Martin. I am stuck at the airport terminal and my corporate card was declined. I need you to approve the authorization code we just sent to your phone. Read it back to me quickly, my flight is boarding.",
            "flags": [
                {"match": "authorization code", "note": "No legitimate caller needs your one-time code."},
                {"match": "Read it back to me", "note": "Asking you to disclose an MFA code."},
                {"match": "my flight is boarding", "note": "Manufactured urgency."},
                {"match": "card was declined", "note": "A plausible pretext for an unusual request."},
            ],
        },
        {
            "id": "audio-helpdesk", "title": "Automated helpdesk PIN retrieval", "difficulty": "Medium",
            "caller": "Unknown number (\"IT Helpdesk\")", "speaker": "Interactive voice response",
            "script": "This is the IT helpdesk automated line. We noticed unusual activity on your workstation. To secure your account, please enter your six digit MFA pin after the beep.",
            "flags": [
                {"match": "enter your six digit MFA pin", "note": "IT never asks for MFA codes by phone."},
                {"match": "unusual activity", "note": "Vague alarm to trigger compliance."},
                {"match": "automated line", "note": "Robocalls are cheap to spoof and hard to question."},
            ],
        },
    ],
}

MODULES = {
    "URL Typosquatting & SSL Spoofing": {
        "modality": "url", "minutes": 6,
        "summary": "Links are the most-clicked lure in your organisation. Learn to read where a link really goes before you trust it.",
        "tips": [
            {"title": "Read the domain from the right", "body": "The part just before the first single slash decides who owns the page. In login.halvard.co.evil.example the owner is evil.example, not Halvard."},
            {"title": "Check every character", "body": "Attackers swap look-alike characters: a zero for an o, 'rn' for 'm', a Cyrillic 'а' for a Latin 'a'. micros0ft.com is not microsoft.com."},
            {"title": "The padlock is not a safety seal", "body": "HTTPS only means the connection is encrypted. Phishing sites get certificates in minutes. Judge the domain, not the padlock."},
        ],
    },
    "Urgency & Pretext Email Scams": {
        "modality": "text", "minutes": 5,
        "summary": "Pressure is the attacker's main tool. Spot the emotional triggers and the process shortcuts they rely on.",
        "tips": [
            {"title": "Deadlines are a red flag", "body": "'Within 2 hours', 'before end of day', 'account suspended'. Real processes rarely give you minutes to act."},
            {"title": "Compare display name and address", "body": "'Diane Keller (CFO)' can be typed by anyone. The address after it (a gmail.com account, a look-alike domain) tells the truth."},
            {"title": "Verify out of band", "body": "For payments, credential resets or data requests, contact the person through a channel you already trust: the directory phone number, not the reply button."},
        ],
    },
    "QR Code & Visual Brand Spoofing": {
        "modality": "image", "minutes": 5,
        "summary": "Images hide what text would reveal. QR codes and screenshots of login panels bypass the link checks you normally do.",
        "tips": [
            {"title": "Treat QR codes as unknown links", "body": "A QR code is a link you can't read. Preview the destination on your phone before opening it, and never scan one to pay an invoice."},
            {"title": "A picture of a button is not a button", "body": "Screenshots of 'storage full' or 'sign in' panels are just images wrapped in a link. Go to the service directly instead."},
            {"title": "Logos cost nothing to copy", "body": "Perfect branding proves nothing. Check the sender domain and whether you expected the message."},
        ],
    },
    "Deepfake Voice & Vishing Defense": {
        "modality": "audio", "minutes": 6,
        "summary": "Seconds of public audio are enough to clone a voice. The request, not the voice, is what gives an attack away.",
        "tips": [
            {"title": "Hang up and call back", "body": "If a caller asks for money, codes or access, end the call and ring the person on the number in the company directory."},
            {"title": "Never read out a one-time code", "body": "MFA codes are for you alone. No helpdesk, bank or executive will ever need you to say one aloud."},
            {"title": "Agree on a verification phrase", "body": "Teams that handle payments can agree a spoken challenge phrase that a voice clone won't know."},
        ],
    },
    "Pause Before You Click": {
        "modality": None, "minutes": 4,
        "summary": "You tend to act on messages within seconds. The model finds fast reactions are one of the strongest predictors of a click.",
        "tips": [
            {"title": "Count to five", "body": "A five-second pause is enough to notice the sender, the deadline and the link. Speed is what attackers design for."},
            {"title": "Be extra careful after hours", "body": "Tired, mobile, late-evening reading is when most simulation clicks happen. Flag it and deal with it in the morning."},
            {"title": "Hover, then decide", "body": "On desktop, hover over a link to see its real address before clicking. On mobile, long-press to preview."},
        ],
    },
    "Report It: Using the Phish Alert Button": {
        "modality": None, "minutes": 3,
        "summary": "Reporting is the behaviour that protects everyone. People who report rarely click.",
        "tips": [
            {"title": "Report, don't just delete", "body": "Deleting protects you. Reporting protects the colleague who gets the same message five minutes later."},
            {"title": "Reporting a real email is fine", "body": "A false alarm costs the security team seconds. A missed phish can cost weeks."},
            {"title": "Clicked by mistake? Report anyway", "body": "Tell the security team immediately. Fast reporting after a click is the difference between an incident and a near miss."},
        ],
    },
    "Security Awareness Refresher": {
        "modality": None, "minutes": 7,
        "summary": "Your last training was a while ago, and the model sees protection fade after roughly six months.",
        "tips": [
            {"title": "Attacks follow the news", "body": "Tax season, benefits enrolment, parcel deliveries: lures change with the calendar, so check for timing that is too convenient."},
            {"title": "Multimodal is the new normal", "body": "Phishing now arrives as QR codes, voice calls and chat messages, not only email. The same pause-and-verify rules apply."},
            {"title": "When in doubt, verify", "body": "Use a channel you already trust to confirm any unexpected request for money, data or access."},
        ],
    },
    "Set Up Multi-Factor Authentication": {
        "modality": None, "minutes": 3,
        "summary": "MFA stops most stolen-password attacks. Your account doesn't have it enabled yet.",
        "tips": [
            {"title": "Enable an authenticator app", "body": "App-based or hardware-key MFA is far stronger than SMS codes."},
            {"title": "Beware MFA fatigue", "body": "If you get a login prompt you didn't start, deny it and report it. Attackers spam prompts hoping you'll tap 'approve'."},
            {"title": "Never share codes", "body": "A code is proof that you are logging in. Anyone asking for it is trying to log in as you."},
        ],
    },
}

# Quiz bank. kind "verdict": answer is "phish" or "legit". kind "choice": answer is an option id.
QUIZ = [
    {
        "id": "q-url-typo", "modality": "url", "kind": "choice",
        "prompt": "You receive \"Action Required: Emergency Office365 Re-authentication\" containing this link. Which single indicator proves it is phishing?",
        "artifact": {"type": "url", "url": "http://login.micros0ft-verify-portal.com/auth/login?session=8823"},
        "options": [
            {"id": "A", "text": "It uses HTTP instead of HTTPS and typosquats \"micros0ft\" with a zero."},
            {"id": "B", "text": "The email was sent during regular work hours."},
            {"id": "C", "text": "It asks you to re-authenticate."},
            {"id": "D", "text": "The link contains a session parameter."},
        ],
        "answer": "A",
        "explain": "The domain micros0ft-verify-portal.com is not Microsoft's, and the zero is deliberate. Unencrypted HTTP on a sign-in page is a second giveaway.",
    },
    {
        "id": "q-url-ip", "modality": "url", "kind": "verdict",
        "prompt": "A shared-file notification links here. Phishing or legitimate?",
        "artifact": {"type": "url", "url": "http://192.168.45.102/docs/sharepoint/Q3-Salaries.xlsx"},
        "answer": "phish",
        "explain": "Real file-sharing services use their own domain names. A raw IP address over plain HTTP, dressed up with 'sharepoint' in the path, is a classic lure.",
    },
    {
        "id": "q-url-legit", "modality": "url", "kind": "verdict",
        "prompt": "The intranet homepage links to this benefits page. Phishing or legitimate?",
        "artifact": {"type": "url", "url": "https://halvard.co/benefits/enrolment"},
        "answer": "legit",
        "explain": "It's the company's own registered domain over HTTPS, reached from a page you navigated to yourself. Nothing is asking you to hurry.",
    },
    {
        "id": "q-text-payroll", "modality": "text", "kind": "verdict",
        "prompt": "Phishing or legitimate?",
        "artifact": {"type": "email", "sender": "Payroll Team <payroll@halvard-hr.net>",
                     "subject": "Direct deposit update required by 5 PM today",
                     "body": "Dear employee,\nDue to a system migration your direct deposit details must be re-confirmed by 5 PM today or your salary will be delayed.",
                     "cta": "Confirm bank details"},
        "answer": "phish",
        "explain": "The domain halvard-hr.net is a look-alike. A same-day deadline and a threat to your salary are pressure tactics, and payroll changes never happen through an email link.",
    },
    {
        "id": "q-text-legit", "modality": "text", "kind": "verdict",
        "prompt": "Phishing or legitimate?",
        "artifact": {"type": "email", "sender": "IT Service Desk <servicedesk@halvard.co>",
                     "subject": "Planned VPN maintenance Saturday 06:00 to 08:00",
                     "body": "Hi all,\nThe VPN will be unavailable on Saturday between 06:00 and 08:00 for planned maintenance. No action is needed from you.\nJonas, IT Service Desk"},
        "answer": "legit",
        "explain": "It comes from the real internal domain, contains no link or attachment, asks for nothing and creates no pressure.",
    },
    {
        "id": "q-text-ceo", "modality": "text", "kind": "choice",
        "prompt": "\"Diane Keller (CFO)\" emails asking you to buy gift cards for a client event and send her the codes. What should you do?",
        "artifact": {"type": "email", "sender": "Diane Keller (CFO) <diane.keller.cfo@outlook.com>",
                     "subject": "Quick favour - confidential",
                     "body": "Are you at your desk? I need you to pick up 5 x $200 gift cards for a client event. Scratch them and email me the codes. I'm in back-to-back meetings so email only."},
        "options": [
            {"id": "A", "text": "Buy the cards. She's the CFO and it's urgent."},
            {"id": "B", "text": "Reply to ask whether she's sure."},
            {"id": "C", "text": "Report it, and if needed call the CFO's office on the directory number."},
            {"id": "D", "text": "Forward it to a colleague to handle."},
        ],
        "answer": "C",
        "explain": "Gift-card requests, a personal outlook.com address and 'email only' are the gift-card scam playbook. Replying reaches the attacker. Verify through a channel you already trust.",
    },
    {
        "id": "q-image-qr", "modality": "image", "kind": "verdict",
        "prompt": "This invoice arrives as an image attachment from billing@canva-invoices.net. Phishing or legitimate?",
        "artifact": {"type": "image", "image": "qr-invoice", "caption": "Invoice #88294 - OVERDUE - Scan to pay"},
        "answer": "phish",
        "explain": "Payment by scanning a QR code from an unexpected invoice is a known 'quishing' pattern. The code hides the destination, and the sender domain doesn't belong to the vendor.",
    },
    {
        "id": "q-image-quota", "modality": "image", "kind": "choice",
        "prompt": "An email shows this 'mailbox full' panel as an image, with an 'Expand quota' button. What gives it away?",
        "artifact": {"type": "image", "image": "quota", "caption": "Mailbox storage: 99.8 GB of 100 GB"},
        "options": [
            {"id": "A", "text": "The progress bar colour is wrong."},
            {"id": "B", "text": "The whole panel is a picture, so the button is just a link that can go anywhere."},
            {"id": "C", "text": "Mailboxes can never be full."},
            {"id": "D", "text": "Nothing. It's safe to click."},
        ],
        "answer": "B",
        "explain": "Real quota warnings appear inside your mail client. An image of a panel wrapped in a link bypasses your usual checks. Open the mail app directly instead.",
    },
    {
        "id": "q-audio-ceo", "modality": "audio", "kind": "verdict",
        "prompt": "You get this voicemail. It sounds exactly like your CEO. Phishing or legitimate?",
        "artifact": {"type": "call", "caller": "+44 7700 900418",
                     "transcript": "Hi, it's Martin. My card was declined at the airport. I've just triggered a login code to your phone. Read it back to me so I can get into the travel portal. Quickly, please, we're boarding."},
        "answer": "phish",
        "explain": "Voice clones are convincing, but the request gives it away. Nobody legitimate needs your one-time code. Hang up and call back on the directory number.",
    },
    {
        "id": "q-audio-legit", "modality": "audio", "kind": "verdict",
        "prompt": "Phishing or legitimate?",
        "artifact": {"type": "call", "caller": "Ext. 4410 (Service Desk)",
                     "transcript": "Hi, it's Jonas from the service desk returning your ticket about the broken dock. Your replacement has arrived. You can pick it up at the desk any time today, no need to share any details."},
        "answer": "legit",
        "explain": "It follows up a ticket you opened, comes from an internal extension and asks for nothing sensitive.",
    },
    {
        "id": "q-audio-mfa", "modality": "audio", "kind": "choice",
        "prompt": "An automated 'IT helpdesk' call asks you to enter your MFA pin after the beep. What is the right response?",
        "artifact": {"type": "call", "caller": "Unknown number",
                     "transcript": "This is the IT helpdesk automated line. We noticed unusual activity on your workstation. Please enter your six digit MFA pin after the beep."},
        "options": [
            {"id": "A", "text": "Enter the pin. It's an automated system."},
            {"id": "B", "text": "Hang up and report the call to security."},
            {"id": "C", "text": "Enter a wrong pin to test it."},
            {"id": "D", "text": "Wait for a human agent."},
        ],
        "answer": "B",
        "explain": "IT never asks for MFA codes. Engaging at all confirms your number is live, so hang up and report it.",
    },
]
