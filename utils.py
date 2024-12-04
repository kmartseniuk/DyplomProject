# utils.py

import re
import torch
import numpy as np
from transformers import (
    pipeline,
    AutoTokenizer,
    AutoModelForTokenClassification
)
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import fitz
from sentence_transformers import SentenceTransformer
import gensim.downloader as api
from rank_bm25 import BM25Okapi


def initialize_models():
    # Check if CUDA is available
    use_cuda = torch.cuda.is_available()
    pipeline_device = 0 if use_cuda else -1

    # Load and configure the tokenizer and model for skills
    skill_tokenizer = AutoTokenizer.from_pretrained("jjzha/jobbert_skill_extraction")
    skill_tokenizer.model_max_length = 512  # Set max sequence length

    skill_model = AutoModelForTokenClassification.from_pretrained("jjzha/jobbert_skill_extraction")

    # Create the skill classifier pipeline with 'first' aggregation strategy
    token_skill_classifier = pipeline(
        "token-classification",
        model=skill_model,
        tokenizer=skill_tokenizer,
        aggregation_strategy="first",
        device=pipeline_device,
    )

    # Load and configure the tokenizer and model for knowledge
    knowledge_tokenizer = AutoTokenizer.from_pretrained("jjzha/jobbert_knowledge_extraction")
    knowledge_tokenizer.model_max_length = 512  # Set max sequence length

    knowledge_model = AutoModelForTokenClassification.from_pretrained("jjzha/jobbert_knowledge_extraction")

    # Create the knowledge classifier pipeline with 'first' aggregation strategy
    token_knowledge_classifier = pipeline(
        "token-classification",
        model=knowledge_model,
        tokenizer=knowledge_tokenizer,
        aggregation_strategy="first",
        device=pipeline_device,
    )

    # Load SBERT model
    sbert_model = SentenceTransformer('paraphrase-MiniLM-L6-v2')

    # Load GloVe embeddings
    glove_model = api.load("glove-wiki-gigaword-100")  # 100-dimensional embeddings

    # Initialize TF-IDF Vectorizer
    tfidf_vectorizer = TfidfVectorizer()

    return {
        'token_skill_classifier': token_skill_classifier,
        'token_knowledge_classifier': token_knowledge_classifier,
        'sbert_model': sbert_model,
        'glove_model': glove_model,
        'tfidf_vectorizer': tfidf_vectorizer,
    }

def parse_resume(file_path, token_skill_classifier, token_knowledge_classifier):
    text = extract_text_from_pdf(file_path)
    name = extract_name(text)
    email = extract_email(text)
    phone = extract_phone(text)
    skills, knowledge = extract_skills_and_knowledge(text, token_skill_classifier, token_knowledge_classifier)
    return {
        'name': name,
        'email': email,
        'phone': phone,
        'skills': skills,
        'knowledge': knowledge
    }

def extract_name(text):
    lines = text.strip().split('\n')
    for line in lines[:10]:  # Check the first 10 lines
        line = line.strip()
        if not line:
            continue
        line = re.sub(r'\s+', ' ', line)
        words = line.split()
        if 1 <= len(words) <= 3:
            if all(word[0].isupper() for word in words):
                return line
    return 'Невідомо'

def extract_email(text):
    email_pattern = re.compile(r'[\w\.-]+@[\w\.-]+\.\w+')
    emails = email_pattern.findall(text)
    if emails:
        return emails[0]
    else:
        return ''

def extract_phone(text):
    phone_pattern = re.compile(r'\+?\d[\d\-\(\) ]{9,}\d')
    phones = phone_pattern.findall(text)
    if phones:
        return phones[0]
    else:
        return ''

def aggregate_span(results):
    new_results = []
    if not results:
        return new_results
    current_result = results[0]

    for result in results[1:]:
        # Check if entities are adjacent (i.e., start of the next entity equals end of current entity plus one)
        if result["start"] == current_result["end"] + 1:
            current_result["word"] += " " + result["word"]
            current_result["end"] = result["end"]
        else:
            new_results.append(current_result)
            current_result = result

    new_results.append(current_result)
    return new_results

def extract_skills_and_knowledge(text, token_skill_classifier, token_knowledge_classifier):
    chunk_size = 400  # Adjust as needed
    overlap_size = 50  # Overlap between chunks to capture entities spanning chunks
    text_length = len(text)
    skill_results = []
    knowledge_results = []

    start = 0
    while start < text_length:
        end = min(start + chunk_size, text_length)
        chunk = text[start:end]

        # Expand the chunk to include overlap
        if end < text_length:
            chunk = text[start:end + overlap_size]

        # Process skills
        output_skills = token_skill_classifier(chunk)
        for result in output_skills:
            if result.get("entity_group"):
                result["entity"] = "Skill"
                del result["entity_group"]

            # Adjust positions to the original text
            result["start"] += start
            result["end"] += start
            skill_results.append(result)

        # Process knowledge
        output_knowledge = token_knowledge_classifier(chunk)
        for result in output_knowledge:
            if result.get("entity_group"):
                result["entity"] = "Knowledge"
                del result["entity_group"]

            # Adjust positions to the original text
            result["start"] += start
            result["end"] += start
            knowledge_results.append(result)

        start += chunk_size

    # Aggregate spans
    if len(skill_results) > 0:
        skill_results = aggregate_span(skill_results)
    if len(knowledge_results) > 0:
        knowledge_results = aggregate_span(knowledge_results)

    # Collect skills and knowledge into sets, capitalize, remove duplicates, exclude single-character entities
    skills_set = set()
    for entity in skill_results:
        word = entity['word'].strip()
        if len(word) > 1 and len(word) < 40:  # Exclude single-character entities
            skills_set.add(' '.join([w.capitalize() for w in word.split()]))

    knowledge_set = set()
    for entity in knowledge_results:
        word = entity['word'].strip()
        if len(word) > 1 and len(word) < 40:  # Exclude single-character entities
            knowledge_set.add(' '.join([w.capitalize() for w in word.split()]))

    return list(skills_set), list(knowledge_set)

def parse_job(description, token_skill_classifier, token_knowledge_classifier):
    skills, knowledge = extract_skills_and_knowledge(description, token_skill_classifier, token_knowledge_classifier)
    return skills, knowledge

# 2. Sentence-BERT Similarity
def calculate_similarity_sbert(resume_attributes, job_attributes, sbert_model):
    # Combine the attributes into strings
    resume_text = ' '.join(resume_attributes)
    job_text = ' '.join(job_attributes)

    # Generate embeddings using SBERT
    resume_embedding = sbert_model.encode(resume_text)
    job_embedding = sbert_model.encode(job_text)

    # Calculate cosine similarity
    similarity = cosine_similarity(
        [resume_embedding], [job_embedding]
    )[0][0]

    return similarity

# 3. TF-IDF Similarity
from sklearn.feature_extraction.text import TfidfVectorizer

def calculate_similarity_tfidf(resume_attributes, job_attributes):
    vectorizer = TfidfVectorizer()

    # Combine the attributes into strings
    resume_text = ' '.join(resume_attributes)
    job_text = ' '.join(job_attributes)

    # Перевірка на порожні тексти
    if not resume_text.strip() or not job_text.strip():
        return 0.0

    try:
        # Fit the vectorizer on both texts
        vectorizer.fit([resume_text, job_text])
        tfidf_matrix = vectorizer.transform([resume_text, job_text])

        # Get vectors
        resume_vector = tfidf_matrix[0]
        job_vector = tfidf_matrix[1]

        # Calculate cosine similarity
        similarity = cosine_similarity(resume_vector, job_vector)[0][0]
    except ValueError:
        similarity = 0.0  # Повертаємо 0.0, якщо виникла помилка

    return similarity

# 4. GloVe Embeddings with TF-IDF Weighting
def calculate_similarity_glove(resume_attributes, job_attributes, vectorizer, glove_model):
    # Combine attributes into strings
    resume_text = ' '.join(resume_attributes)
    job_text = ' '.join(job_attributes)

    # Fit the vectorizer on both texts
    vectorizer.fit([resume_text, job_text])

    # Get TF-IDF vectors
    tfidf_resume = vectorizer.transform([resume_text])
    tfidf_job = vectorizer.transform([job_text])

    # Get feature names (vocabulary)
    feature_names = vectorizer.get_feature_names_out()

    # Calculate weighted embeddings
    resume_embedding = get_weighted_embedding(tfidf_resume, feature_names, glove_model)
    job_embedding = get_weighted_embedding(tfidf_job, feature_names, glove_model)

    # Calculate cosine similarity
    similarity = cosine_similarity(
        [resume_embedding], [job_embedding]
    )[0][0]

    return similarity

def get_weighted_embedding(tfidf_vector, feature_names, glove_model):
    indices = tfidf_vector.nonzero()[1]
    weights = tfidf_vector.data
    embedding = np.zeros(glove_model.vector_size)
    weight_sum = 0

    for idx, weight in zip(indices, weights):
        word = feature_names[idx]
        if word in glove_model.key_to_index:
            embedding += weight * glove_model[word]
            weight_sum += weight

    if weight_sum != 0:
        embedding /= weight_sum

    return embedding

# 6. Rank-BM25 Similarity
def calculate_similarity_bm25(resume_attributes, job_attributes):
    resume_text = ' '.join(resume_attributes)
    job_text = ' '.join(job_attributes)

    corpus = [resume_text, job_text]
    tokenized_corpus = [doc.split() for doc in corpus]

    bm25 = BM25Okapi(tokenized_corpus)
    query = job_text.split()
    scores = bm25.get_scores(query)

    # Since we have only two documents, scores[0] is for resume
    similarity = scores[0] / max(scores)  # Normalize the score

    return similarity

def extract_text_from_pdf(file_path):
    try:
        doc = fitz.open(file_path)
        text = ""
        for page in doc:
            page_text = page.get_text()
            if page_text:
                text += page_text + "\n"
        doc.close()
        return text
    except Exception as e:
        print(f"Помилка при витяганні тексту: {e}")
        return ""
