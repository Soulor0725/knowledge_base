import sys
sys.stdout.reconfigure(encoding="utf-8")

content = open("routes/auth.py", "r", encoding="utf-8").read()

if "/change-password" in content:
    print("Route already exists")
    sys.exit(0)

nl = chr(10)
new_route = f"""\
{nl}{nl}@auth_bp.route("/change-password", methods=["POST"])
@login_required
def change_password():
    \"\"\"修xxxx码\"\"\" 
    data, err = safe_get_json()
    if err:
        return err
    if not data:
        return jsonify({"error": "xxxx"}), 400

    old_password = data.get("old_password", "")
    new_password = data.get("new_password", "")

    if not old_password or not new_password:
        return jsonify({"error": "xxxx"}), 400

    if len(new_password) < PASSWORD_MIN_LENGTH:
        return jsonify({"error": "xxxx"}), 400
    if not (any(c.isupper() for c in new_password) and any(c.islower() for c in new_password) and any(c.isdigit() for c in new_password)):
        return jsonify({"error": "xxxx"}), 400

    if old_password == new_password:
        return jsonify({"error": "xxxx"}), 400

    db = get_db()
    cursor = db.cursor()
    cursor.execute("SELECT password FROM users WHERE id = ?", (g.user_id,))
    row = cursor.fetchone()
    if not row:
        return jsonify({"error": "xxxx"}), 404

    if not pbkdf2_sha256.verify(old_password, row["password"]):
        return jsonify({"error": "xxxx"}), 401

    hashed_password = pbkdf2_sha256.hash(new_password)
    cursor.execute("UPDATE users SET password = ? WHERE id = ?", (hashed_password, g.user_id))
    safe_commit(db)

    logger.info("user %d changed password", g.user_id)
    return jsonify({"message": "xxxx"}), 200
"""

content = content.rstrip() + new_route + nl
open("routes/auth.py", "w", encoding="utf-8").write(content)
print("Route added successfully")