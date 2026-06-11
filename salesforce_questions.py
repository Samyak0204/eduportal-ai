# Salesforce Sample Questions for EduPortal AI

DUMMY_QUESTIONS = [
    {
        "title": "Salesforce Security: Role Hierarchy vs Sharing Rules",
        "type": "Multiple Choice",
        "text": "Which of the following statements is true regarding Role Hierarchy and Sharing Rules in Salesforce?",
        "options": {
            "A": "Role Hierarchy can restrict access that is granted by Org-Wide Defaults, whereas Sharing Rules can only open up access.",
            "B": "Role Hierarchy automatically grants record access to users above the record owner in the hierarchy, while Sharing Rules are used to open up access horizontally to other roles or groups.",
            "C": "Sharing Rules can restrict record access to users below in the role hierarchy.",
            "D": "Both A and B are correct."
        },
        "correct_option": "B",
        "explanation": "The Role Hierarchy automatically grants access to record owners' managers/supervisors (vertical sharing), while Sharing Rules are used to grant access laterally (horizontally) to public groups, roles, or territories. Neither can restrict access; they only open up access beyond Org-Wide Defaults (OWD).",
        "difficulty": "Medium",
        "marks": 10,
        "allowed_formats": ["Text"]
    },
    {
        "title": "Salesforce Data Model: Master-Detail vs Lookup",
        "type": "Free Text / Essay",
        "text": "Explain the key differences between a Master-Detail Relationship and a Lookup Relationship in Salesforce. Consider ownership, security, deletion behavior, and roll-up summary fields.",
        "explanation": "In a Master-Detail relationship: 1. Detail records inherit security and sharing settings from the master. 2. Deleting a master record automatically deletes all detail records. 3. Master-detail fields are required. 4. Roll-up summary fields can be created on the master. In a Lookup relationship: 1. Records have independent sharing. 2. Deleting the parent does not delete child records. 3. The field is optional. 4. No roll-up summaries exist by default.",
        "difficulty": "Medium",
        "marks": 10,
        "allowed_formats": ["Text", "Image", "Audio"]
    },
    {
        "title": "Apex Development: Prevent Duplicate Leads",
        "type": "Code Problem",
        "text": "Write a simple Apex trigger outline (before insert) that prevents duplicate Lead records from being created if a Lead with the same Email address already exists in Salesforce. Use appropriate Apex collection patterns and add an error message to the duplicate records.",
        "explanation": "The trigger should operate on 'before insert'. It must gather all emails from Trigger.new into a Set, query the database for existing Leads matching those emails, store the existing emails in a Set, and then loop through Trigger.new to check if email is in the existing set. If so, call lead.Email.addError('A Lead with this Email already exists.'). This prevents the SOQL-in-loop anti-pattern.",
        "difficulty": "Hard",
        "marks": 15,
        "allowed_formats": ["Text", "Image"]
    },
    {
        "title": "Salesforce System Architecture: Identity Confirmation",
        "type": "Image-Based",
        "text": "Draw or describe the sequence diagram of a Salesforce User Authentication Flow (OAuth 2.0 Web Server Flow) using webcam capture or text. Make sure to identify client, authorization server, and resource server roles.",
        "explanation": "The OAuth 2.0 Web Server Flow involves: 1. User accesses application. 2. App redirects user to Salesforce authorization endpoint. 3. User logs in and approves access. 4. Salesforce redirects user back to app redirect URI with authorization code. 5. App requests access token by sending client credentials and authorization code to Salesforce token endpoint. 6. Salesforce validates and returns access token and refresh token. 7. App uses access token to make API requests.",
        "difficulty": "Hard",
        "marks": 15,
        "allowed_formats": ["Image", "Text"]
    },
    {
        "title": "Salesforce Automation: Post-Validation Automations",
        "type": "Multiple Choice",
        "text": "In Salesforce, which of the following automations execute AFTER custom Validation Rules run during a record save? (Select all that apply)",
        "options": {
            "A": "Escalation Rules",
            "B": "Assignment Rules",
            "C": "Workflow Rules",
            "D": "Before-Save Flows"
        },
        "correct_option": ["A", "B", "C"],
        "is_multi_correct": True,
        "explanation": "During a record save, Salesforce validation rules run before Assignment Rules, Workflow Rules, and Escalation Rules. Before-Save flows run BEFORE validation rules. Thus, A, B, and C execute after validation rules.",
        "difficulty": "Medium",
        "marks": 10,
        "allowed_formats": ["Text"]
    }
]
