from flask import Flask, jsonify
import instaloader
import os
import time

app = Flask(__name__)
L = instaloader.Instaloader()

# OPTIONAL LOGIN (recommended to avoid 429)
# L.login("your_username", "your_password")

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
                "full_name": profile.full_name,
                "bio": profile.biography,
                "followers": profile.followers,
                "following": profile.followees,
                "posts_count": profile.mediacount
            },
            "posts": []
        }

        for i, post in enumerate(profile.get_posts()):
            if i >= 5:
                break

            data["posts"].append({
                "post_url": f"https://www.instagram.com/p/{post.shortcode}/",
                "likes": post.likes,
                "comments": post.comments,
                "caption": post.caption
            })

            time.sleep(2)  # prevent 429

        return jsonify(data)

    except Exception as e:
        return jsonify({
            "developer": "Shayon Explorer",
            "status": "error",
            "message": str(e)
        })

# IMPORTANT FOR RAILWAY
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    app.run(host="0.0.0.0", port=port)
