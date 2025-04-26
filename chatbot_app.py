# Final Corrected RelEase App: No Duplicate Outputs, Full Functionality

import dash
from dash import dcc, html
from dash.dependencies import Input, Output, State
import base64
import io
import PyPDF2
import docx
import re
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
from autocorrect import Speller

external_stylesheets = [
    'https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;600;700&display=swap'
]

app = dash.Dash(__name__, external_stylesheets=external_stylesheets)

# Initialize models
embedder = SentenceTransformer('all-MiniLM-L6-v2')
spell = Speller(lang='en')

# Global vars
conversation = []
sections = {}
section_titles = []
section_contents = []
section_embeddings = []

# Extraction Functions

def extract_text_from_pdf(file):
    text = ""
    reader = PyPDF2.PdfReader(file)
    for page in reader.pages:
        page_text = page.extract_text()
        if page_text:
            text += page_text
    return text

def extract_text_from_docx(file):
    text = ""
    doc = docx.Document(file)
    for para in doc.paragraphs:
        text += para.text + " "
    return text

def extract_text_from_txt(file):
    return file.read().decode('utf-8')

def split_into_sections(text):
    sections = {}
    patterns = {
        "Product Info": r'Product:\s*(.*?)\s*Version',
        "Version Info": r'Version\s*(.*?)\s*New Features',
        "New Features": r'New Features:\s*(.*?)(?:Bug Fixes:|Known Issues:|End of Support:|Version History:|$)',
        "Bug Fixes": r'Bug Fixes:\s*(.*?)(?:Known Issues:|End of Support:|Version History:|$)',
        "Known Issues": r'Known Issues:\s*(.*?)(?:End of Support:|Version History:|$)',
        "End of Support": r'End of Support:\s*(.*?)(?:Version History:|$)',
        "Version History": r'Version History:\s*(.*)'
    }
    for section, pattern in patterns.items():
        match = re.search(pattern, text, re.DOTALL | re.IGNORECASE)
        if match:
            content = match.group(1).strip()
            if content:
                sections[section] = content
    return sections

def process_uploaded_file(contents, filename):
    global sections, section_titles, section_contents, section_embeddings
    content_type, content_string = contents.split(',')
    decoded = base64.b64decode(content_string)
    file = io.BytesIO(decoded)

    if filename.endswith('.pdf'):
        text = extract_text_from_pdf(file)
    elif filename.endswith('.docx'):
        text = extract_text_from_docx(file)
    elif filename.endswith('.txt'):
        text = extract_text_from_txt(file)
    else:
        return "\u274c Unsupported file format. Please upload PDF, DOCX, or TXT."

    if not text.strip():
        return "\u274c Error reading file. Please upload a valid file."

    sections = split_into_sections(text)

    if not sections:
        return "\u274c Invalid release notes uploaded. Please upload a valid file with proper sections."

    section_titles = list(sections.keys())
    section_contents = list(sections.values())
    full_sections = [title + " " + content for title, content in sections.items()]
    section_embeddings = embedder.encode(full_sections)

    return "\u2705 File uploaded successfully! You can now ask your questions."

def clean_response(text):
    text = re.sub(r'^\s*-\s*', '', text, flags=re.MULTILINE)
    text = re.sub(r'\s*-\s*', ' ', text)
    return text.strip()

def find_best_section(user_query):
    if not sections:
        return "Error: No release notes loaded. Please upload a valid file first."

    corrected_query = spell(user_query)
    query = corrected_query.lower()

    # Priority Order Matching
    if any(word in query for word in
           ["bug", "bugs", "fix", "fixed", "resolved", "resolve", "solved", "patch", "hotfix", "issue fixed",
            "problems fixed", "bugs resolved", "crashes fixed", "errors corrected"]):
        section = "Bug Fixes"
    elif any(word in query for word in ["feature", "features", "improvement", "improvements", "enhancement", "enhancements", "newly added", "introduced", "new functionality", "what's new"]):
        section = "New Features"
    elif any(word in query for word in ["known issues", "existing problems", "open issues", "still pending bugs", "unsolved issues", "limitations", "unresolved problems", "current issues"]):
        section = "Known Issues"
    elif any(word in query for word in ["end of support", "support end", "maintenance end", "lifecycle end", "updates end", "retirement date", "support termination", "deprecation notice"]):
        section = "End of Support"
    elif any(word in query for word in ["version history", "past versions", "previous releases", "previous updates", "evolution", "changelog", "release history", "prior versions"]):
        section = "Version History"
    elif any(word in query for word in ["update", "latest update", "release date", "new release", "version date", "current version", "release information"]):
        section = "Version Info"
    elif any(word in query for word in ["product", "software", "product name", "document about", "release notes for", "which product", "application name", "software title"]):
        section = "Product Info"
    else:
        # Semantic fallback if nothing matches keywords
        user_embedding = embedder.encode([corrected_query])
        similarities = cosine_similarity(user_embedding, section_embeddings)
        best_index = similarities.argmax()

        if similarities[0, best_index] >= 0.4:
            section = section_titles[best_index]
        else:
            return "Sorry, I couldn't find any relevant information for your question."

    if section not in sections:
        return "Sorry, I couldn't find any relevant information for your question."

    answer = clean_response(sections[section])

    if section == "New Features":
        return f"The new features of the product in this release are:\n{answer}"
    elif section == "Bug Fixes":
        return f"The bug fixes included in this release are:\n{answer}"
    elif section == "Known Issues":
        return f"The known issues reported in this release are:\n{answer}"
    elif section == "End of Support":
        return f"Regarding end of support, here is the information:\n{answer}"
    elif section == "Version History":
        return f"The version history details are:\n{answer}"
    elif section == "Product Info":
        return f"This release is about the product:\n{answer}"
    elif section == "Version Info":
        return f"The version and release date details are:\n{answer}"
    else:
        return f"{answer}"

# Layout
def serve_layout():
    return html.Div(
        style={
            'backgroundColor': '#121212',
            'fontFamily': 'Poppins, sans-serif',
            'minHeight': '100vh',
            'padding': '20px'
        },
        children=[
            html.H1("RelEase", style={
                'textAlign': 'center',
                'color': 'white',
                'marginBottom': '30px',
                'fontWeight': '700'
            }),

            dcc.Upload(
                id='upload-data',
                children=html.Div(['📄 Drag and Drop or ', html.A('Select a File')]),
                style={
                    'width': '90%',
                    'margin': 'auto',
                    'padding': '20px',
                    'borderWidth': '2px',
                    'borderStyle': 'dashed',
                    'borderRadius': '10px',
                    'borderColor': '#aaa',
                    'backgroundColor': '#1f1f1f',
                    'textAlign': 'center',
                    'color': '#ccc',
                    'marginBottom': '20px'
                },
                multiple=False
            ),

            html.Div(id='upload-message', style={
                'textAlign': 'center',
                'color': '#4CAF50',
                'marginBottom': '20px',
                'fontSize': '16px'
            }),

            dcc.Textarea(
                id='user-input',
                placeholder='Type your question here...',
                style={
                    'width': '90%',
                    'height': '100px',
                    'borderRadius': '10px',
                    'border': '1px solid #888',
                    'padding': '10px',
                    'fontSize': '16px',
                    'margin': 'auto',
                    'display': 'block',
                    'backgroundColor': '#f4f7fa',
                    'color': '#333',
                    'marginBottom': '20px',
                    'resize': 'none'
                }
            ),

            html.Div([
                html.Button('Ask', id='submit-btn', n_clicks=0, style={
                    'padding': '10px 20px',
                    'backgroundColor': '#2196F3',
                    'color': 'white',
                    'border': 'none',
                    'borderRadius': '5px',
                    'fontSize': '16px',
                    'cursor': 'pointer',
                    'marginRight': '10px'
                }),
                html.Button('Reset Chat', id='reset-btn', n_clicks=0, style={
                    'padding': '10px 20px',
                    'backgroundColor': '#f44336',
                    'color': 'white',
                    'border': 'none',
                    'borderRadius': '5px',
                    'fontSize': '16px',
                    'cursor': 'pointer'
                })
            ], style={'textAlign': 'center'}),

            html.Div(id='output-area', style={
                'backgroundColor': '#f4f7fa',
                'borderRadius': '10px',
                'padding': '20px',
                'minHeight': '300px',
                'marginTop': '30px',
                'marginLeft': 'auto',
                'marginRight': 'auto',
                'width': '90%',
                'boxShadow': '0 4px 8px rgba(0,0,0,0.1)',
                'fontSize': '16px',
                'color': '#333',
                'whiteSpace': 'pre-line'
            })
        ]
    )

app.layout = serve_layout()

# Unified Callback

@app.callback(
    Output('upload-message', 'children'),
    Output('output-area', 'children'),
    Output('user-input', 'value'),
    Input('upload-data', 'contents'),
    Input('submit-btn', 'n_clicks'),
    Input('reset-btn', 'n_clicks'),
    State('upload-data', 'filename'),
    State('user-input', 'value'),
    prevent_initial_call=True
)
def unified_callback(contents, submit_clicks, reset_clicks, filename, user_input):
    global conversation, sections, section_titles, section_contents, section_embeddings
    ctx = dash.callback_context

    if not ctx.triggered:
        raise dash.exceptions.PreventUpdate

    button_id = ctx.triggered[0]['prop_id'].split('.')[0]

    if button_id == 'upload-data' and contents:
        message = process_uploaded_file(contents, filename)
        return message, dash.no_update, dash.no_update

    elif button_id == 'reset-btn':
        conversation = []
        sections = {}
        section_titles = []
        section_contents = []
        section_embeddings = []
        return "No file uploaded. Please upload a valid PDF, DOCX, or TXT file.", "", ""

    elif button_id == 'submit-btn' and user_input:
        response = find_best_section(user_input)
        conversation.append(f"Q: {user_input}\n\nA: {response}\n\n")
        return dash.no_update, "\n".join(conversation), ""

    return dash.no_update, dash.no_update, dash.no_update

if __name__ == '__main__':
    app.run(debug=True)
