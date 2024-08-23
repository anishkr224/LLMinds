import os
from flask import Flask, request, jsonify, render_template
from PyPDF2 import PdfReader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.chains.question_answering import load_qa_chain
from langchain.prompts import PromptTemplate
from dotenv import load_dotenv
import google.generativeai as genai

# Set gRPC logging level
os.environ["GRPC_VERBOSITY"] = "ERROR"
os.environ["GRPC_LOG_SEVERITY"] = "ERROR"

# Load environment variables
load_dotenv()
api_key = os.getenv("GOOGLE_API_KEY")

if not api_key:
    raise ValueError("Google API Key not found. Please set it in the .env file.")
else:
    genai.configure(api_key=api_key)

app = Flask(__name__)

vector_store = None

def get_pdf_text(pdf_docs):
    text = ""
    for pdf in pdf_docs:
        pdf_reader = PdfReader(pdf)
        for page in pdf_reader.pages:
            text += page.extract_text()
    return text

def get_text_chunks(text):
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=10000, chunk_overlap=1000)
    chunks = text_splitter.split_text(text)
    return chunks

def get_vector_store(text_chunks):
    embeddings = GoogleGenerativeAIEmbeddings(model="models/embedding-001")
    vector_store = FAISS.from_texts(text_chunks, embedding=embeddings)
    vector_store.save_local("faiss_index")
    return vector_store

def get_conversational_chain():
    prompt_template = """
    Answer the question as detailed as possible from the provided context. If the answer is not in the provided context, clearly state, "The provided context does not mention anything about [subject], so I cannot answer this question from the provided context." Do not provide an answer not found in the context.\n\n
    Context:\n{context}\n
    Question:\n{question}\n
    Answer:
    """
    model = ChatGoogleGenerativeAI(model="gemini-pro", temperature=0.3)
    prompt = PromptTemplate(template=prompt_template, input_variables=["context", "question"])
    chain = load_qa_chain(model, chain_type="stuff", prompt=prompt)
    return chain

# Function to load OpenAI model and get responses
model = genai.GenerativeModel('gemini-pro')
def get_gemini_response(user_question):
    response = model.generate_content(user_question)
    return response

def load_pdfs_from_directory(directory):
    pdf_files = [os.path.join(directory, file) for file in os.listdir(directory) if file.endswith('.pdf')]
    raw_text = get_pdf_text(pdf_files)
    text_chunks = get_text_chunks(raw_text)
    global vector_store
    vector_store = get_vector_store(text_chunks)

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/ask', methods=['POST'])
def ask():
    user_question = request.json.get('question')
    if not user_question:
        return jsonify({"error": "No question provided"}), 400

    if vector_store is None:
        return jsonify({"error": "No vector store available"}), 500

    try:
        embeddings = GoogleGenerativeAIEmbeddings(model="models/embedding-001")
        new_db = FAISS.load_local("faiss_index", embeddings, allow_dangerous_deserialization=True)
        docs = new_db.similarity_search(user_question)
        chain = get_conversational_chain()
        response = chain.invoke({"input_documents": docs, "question": user_question}, return_only_outputs=True)

        if "The provided context does not mention anything about" in response["output_text"]:
            # Fallback to Gemini if the answer is not found in the context
            fallback_response = get_gemini_response(user_question).text.strip()
            return jsonify({"answer": fallback_response}), 200
        else:
            return jsonify({"answer": response["output_text"]}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    pdf_directory = "./us_census"  # Specify the directory containing PDFs
    load_pdfs_from_directory(pdf_directory)
    app.run(debug=True)