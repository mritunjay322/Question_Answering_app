import os, tempfile, streamlit as st
from langchain_pinecone import PineconeVectorStore
from langchain.chains import RetrievalQA
from langchain_community.document_loaders import PyPDFLoader
from langchain_groq import ChatGroq
from langchain_cohere import CohereEmbeddings

# Streamlit app
st.subheader("Document Question-Answering App")

# Sidebar for settings and source file upload
with st.sidebar:
    st.subheader("Settings")
    groq_api_key = st.text_input("Groq API key", type="password")
    cohere_api_key = st.text_input("Cohere API key", type="password")
    pinecone_api_key = st.text_input("Pinecone API key", type="password")
    pinecone_index = st.text_input("Pinecone index name")
    source_doc = st.file_uploader("Source document", type="pdf")
query = st.text_input("Enter your query")

# Set environment variables for API keys

os.environ['PINECONE_API_KEY'] = pinecone_api_key
os.environ['GROQ_API_KEY']=groq_api_key
os.environ['COHERE_API_KEY']=cohere_api_key

# Session state initialization for documents and retrievers
if 'retriever' not in st.session_state or 'loaded_doc' not in st.session_state:
    st.session_state.retriever = None
    st.session_state.loaded_doc = None

submit = st.button("Submit")

if submit:
    # Validate inputs
    if not groq_api_key or not pinecone_api_key or not pinecone_index or not source_doc or not query:
        st.warning(f"Please upload the document and provide the missing fields.")
    else:
        with st.spinner("Please wait..."):
            # Check if it's the same document; if not or if retriever isn't set, reload and recompute
            if st.session_state.loaded_doc != source_doc:
                try:
                    # Save uploaded file temporarily to disk, load and split the file into pages, delete temp file
                    with tempfile.NamedTemporaryFile(delete=False) as tmp_file:
                        tmp_file.write(source_doc.read())
                    loader = PyPDFLoader(tmp_file.name)
                    pages = loader.load_and_split()
                    os.unlink(tmp_file.name)
    
                    # Generate embeddings for the pages, insert into Pinecone vector database, and expose the index in a retriever interface
                    
                    embeddings = CohereEmbeddings()
                    vectorstore = PineconeVectorStore.from_documents(pages, embeddings, index_name=pinecone_index)
                    st.session_state.retriever = vectorstore.as_retriever()
    
                    # Store the uploaded file in session state to prevent reloading
                    st.session_state.loaded_doc = source_doc
                except Exception as e:
                    st.error(f"An error occurred: {e}")
    
            try:
                # Initialize the OpenAI module, load and run the Retrieval Q&A chain
                llm=ChatGroq(groq_api_key=groq_api_key, model_name="Llama3-8b-8192")
                qa = RetrievalQA.from_chain_type(llm, chain_type="stuff", retriever=st.session_state.retriever)
                response = qa.run(query)
                
                st.success(response)
            except Exception as e:
                st.error(f"An error occurred: {e}")