from flask import Flask, jsonify
import instaloader
import os
import time

app = Flask(__name__)
L = instaloader.Instaloader()

@app.route('/')
def home():
    return jsonify({
        "message": "Instagram API is running",
        "developer": "Shayon Explorer"
    })

@app.route('/user/<username>')
def get_user(username):
    try:
        profile = instaloader.Profile.from_username(L.context, username)

        data = {
            "developer": "Shayon Explorer",
            "status": "success",
            "profile": {
                "username": profile.username,
                "followers": profile.followers
            },
            "posts": []
        }

        for i, post in enumerate(profile.get_posts()):
            if i >= 3:
                break

            data["posts"].append({
                "url": f"https://www.instagram.com/p/{post.shortcode}/",
                "likes": post.likes,
                "comments": post.comments
            })

            time.sleep(2)

        return jsonify(data)

    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        })

# ✅ IMPORTANT FIX
port = int(os.environ.get("PORT", 8000))

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=port)
