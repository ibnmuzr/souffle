"""Manage Promotions (UC 05): interactive screen for the manager.

Create a promotion and save it as a draft or share it, edit a draft, share a draft,
and see every promotion with its state, validity and engagement.

Run from the project folder:  python3 manage_promotions.py
"""
from contextlib import closing
from datetime import date

from database.connection import DB_PATH, get_connection
from database.setup_db import create_database
from models import Promotion
from models.people import load_manager
from models.promotions import SHARING_CHANNELS, next_promotion_id


def ask(prompt, default=""):
    shown = f" [{default}]" if default else ""
    answer = input(f"{prompt}{shown}: ").strip()
    return answer or default


def ask_date(prompt, default):
    text = ask(prompt, default)
    try:
        return date.fromisoformat(text)
    except ValueError:
        raise ValueError("Please use the format YYYY-MM-DD.")


def ask_value(prompt, default=""):
    text = ask(prompt, default)
    return int(text) if text.isdigit() else -1


def list_promotions():
    with closing(get_connection()) as conn:
        ids = [r[0] for r in conn.execute("SELECT promotionID FROM promotions ORDER BY promotionID")]
    for promotionID in ids:
        p = Promotion.getPromotion(promotionID)
        off = f"{p.discountValue}%" if p.discountType == "percentage" else f"${p.discountValue}"
        print(f"  {p.promotionID}  {p.title:<20}{off:>5} off  {p.startDate} to {p.endDate}  "
              f"{p.lifecycleState:<8} valid now: {'yes' if p.isValid(promotionID) else 'no ':<4}"
              f"used by {p.trackEngagement(promotionID)} order(s)")


def create(manager):
    today = date.today()
    promotion = Promotion(0, "", "", 0, today, today, today, "", "", managerID=manager.managerID)
    promotion.createPromotion(
        next_promotion_id(), ask("Title"),
        ask("Discount type (percentage / fixed)", "percentage"),
        ask_value("Discount value (percent or dollars)"),
        ask_date("Start date", today.isoformat()), ask_date("End date", today.isoformat()))
    if ask("Share it now (s) or save as a draft (d)", "d").lower() == "s":
        print("Sending:")
        promotion.sharePromotion(promotion.promotionID,
                                 ask(f"Channel ({' / '.join(SHARING_CHANNELS)})", "email"))
        print(f"  Promotion {promotion.promotionID} shared.")
    else:
        promotion.saveDraft(promotion.promotionID)
        print(f"  Promotion {promotion.promotionID} saved as a draft.")


def edit_or_share():
    promotionID = ask_value("Promotion ID")
    promotion = Promotion.getPromotion(promotionID)
    if promotion is None:
        print("  There is no such promotion.")
        return
    if ask("Edit the draft (e) or share it (s)", "e").lower() == "s":
        print("Sending:")
        promotion.sharePromotion(promotionID, ask(f"Channel ({' / '.join(SHARING_CHANNELS)})", "email"))
        print(f"  Promotion {promotionID} shared.")
        return
    title = ask("New title (Enter to keep)")
    value = ask("New discount value (Enter to keep)")
    promotion.editDraft(promotionID, title=title or None,
                        discountValue=int(value) if value.isdigit() else None)
    print(f"  Draft {promotionID} saved.")


def main():
    if not DB_PATH.exists():
        create_database()
    manager = load_manager(1)
    print("=== Soufflé: Manage Promotions ===")
    print(f"Logged in as manager {manager.getFullName()}")
    while True:
        print("\n1 List promotions   2 New promotion   3 Edit or share a draft   q Quit")
        choice = ask("Choose", "1").lower()
        if choice == "q":
            break
        try:
            {"1": list_promotions, "2": lambda: create(manager), "3": edit_or_share}.get(
                choice, lambda: print("  Please choose 1, 2, 3 or q."))()
        except ValueError as err:
            print(f"  {err}")
    print("Goodbye.")


if __name__ == "__main__":
    main()
