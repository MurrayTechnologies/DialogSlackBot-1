

def get_attachments(submission):
    fields = [
        {
            "title": key.replace("_", " ").title(),
            "value": value
        }
        for key, value in submission.items()
    ]
    attachment = {
        "color": "#aaefab",
        "mrkdwn_in": ['fields', 'text', 'pretext'],
        "fields": fields,
        'footer': 'Category',
    }
    return [attachment]
