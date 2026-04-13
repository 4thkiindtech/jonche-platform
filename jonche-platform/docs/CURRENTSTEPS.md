Great — here’s the **Monday execution package** you can hand directly to your dev team. This locks messaging, defines tiers, and specifies **pages + intake forms** for your PythonAnywhere stack. 🚀

---

# 🧭 Program Structure (Finalized)

### Programs

* **Jonche Retail Alliance**
* **Jonche Strategic Referral Network**
* **Jonche Affiliate Creators**
* **Jonche Executives (High-level connectors)**

---

# 💰 Commission Structure (Final)

* Affiliate creators → **10–15% per sale**
* Bulk referral partners → **20% wholesale order commission**
* Strategic funding referrals → **25% of earned funding commission**

---

# 🧩 Required Pages (Dev Team)

Create **four public pages + four intake forms**:

1. `/retail-alliance`
2. `/affiliates`
3. `/referral-network`
4. `/executives`

Each page:

* overview
* benefits
* commission structure
* CTA
* intake form

---

# 📄 One-Page Overview (Bullet Format)

This content should appear on `/partners` or homepage section.

## Jonche Partnership Programs

**We help partners grow through exclusive footwear, funding access, and referral commissions.**

### Jonche Retail Alliance

* Exclusive sneaker allocations
* Co-branded opportunities
* Marketing support
* Funding access (if qualified)
* POS system options
* Early product releases

### Jonche Affiliate Creators

* 10–15% per sale
* Unique referral link
* Early access to drops
* Creator spotlight opportunities
* Performance bonuses

### Jonche Strategic Referral Network

* 20% bulk order commissions
* 25% funding referral commissions
* Priority payouts
* Partner recognition
* High-ticket deal opportunities

### Jonche Executives

* Premium deal flow
* Larger commission eligibility
* Co-brand opportunities
* Territory partnerships
* Direct collaboration with Jonche leadership

---

# 📝 Intake Form Fields (Standardized)

Use same backend but different `program_type`.

### Required Fields

* Full Name
* Business Name (optional)
* Email
* Phone
* Website / Social Link
* City / State
* Program Applying For (auto-filled)
* Estimated Monthly Reach
* Type of Network (dropdown)
* Interested In:

  * Selling products
  * Referrals
  * Funding introductions
  * Retail partnership
* Additional Notes

---

# 🧠 Flask Backend Structure (PythonAnywhere)

Your devs should create:

```
/jonche
  /templates
    affiliates.html
    retail_alliance.html
    referral_network.html
    executives.html
  /routes
    partners.py
  /models
    partner.py
```

---

# Example Flask Route

```python
from flask import Blueprint, render_template, request, redirect
from models.partner import Partner
from app import db

partners = Blueprint('partners', __name__)

@partners.route('/affiliates', methods=['GET','POST'])
def affiliates():
    if request.method == 'POST':
        new_partner = Partner(
            name=request.form['name'],
            email=request.form['email'],
            phone=request.form['phone'],
            program='affiliate',
            notes=request.form['notes']
        )
        db.session.add(new_partner)
        db.session.commit()
        return redirect('/thank-you')
    return render_template('affiliates.html')
```

---

# Database Model

```python
from app import db

class Partner(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120))
    email = db.Column(db.String(120))
    phone = db.Column(db.String(50))
    program = db.Column(db.String(50))
    notes = db.Column(db.Text)
```

---

# HTML Intake Form (Reusable)

```html
<form method="POST">
  <input type="text" name="name" placeholder="Full Name" required>
  <input type="email" name="email" placeholder="Email" required>
  <input type="text" name="phone" placeholder="Phone">
  <textarea name="notes" placeholder="Tell us about your network"></textarea>
  <button type="submit">Apply Now</button>
</form>
```

---

# Page CTA Messaging

### Affiliates Page

"Earn 10–15% promoting exclusive Jonche releases."

### Retail Alliance Page

"Offer exclusive sneakers and grow your store revenue."

### Referral Network Page

"Earn high commissions connecting businesses and buyers."

### Executives Page

"Partner with Jonche on premium deals and strategic growth."

---

# Deliverables (End of Monday)

Your dev team should produce:

* 4 landing pages
* 4 intake forms
* database table
* submission storage
* confirmation page
* admin view (optional but ideal)

---

# Priority Order for Dev Team

1. Database model
2. Form submission working
3. Pages created
4. Styling later

Functionality first.

---

Once this is live, Tuesday becomes:

* outreach
* recruitment
* deal pipeline

You’ll officially have your **partner infrastructure running.**
