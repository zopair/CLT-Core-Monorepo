
def apply_refund_policy(payment_amount):
    # تطبيق سياسة البرنس سلطان: استرجاع المبلغ بخصم 10%
    admin_fees = payment_amount * 0.10
    refund_amount = payment_amount - admin_fees
    return refund_amount, admin_fees

def get_guarantee_statement():
    return (
        "🛡️ **Al-Zubair Quality Guarantee:** \n"
        "If the product is proven to be inefficient or doesn't match your specific requirements, "
        "a refund is guaranteed with only a 10% administrative fee deduction.\n"
        "Your trust is our priority."
    )
