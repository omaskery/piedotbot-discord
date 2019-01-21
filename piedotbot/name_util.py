

def display_user_display_names(user_like):
    if user_like.name == user_like.display_name:
        return user_like.name
    else:
        return f"{user_like.display_name} ({user_like.name})"
