import pickle
import os
import torch
import glob
import logging
import warnings
from sentence_transformers import SentenceTransformer
import numpy as np
from numpy.typing import NDArray

logging.basicConfig(format='%(asctime)s : %(levelname)s : %(message)s', level=logging.INFO)
warnings.simplefilter(action='ignore', category=FutureWarning)

CORPUS_PATH = os.getcwd()
EMNET_PATH = os.path.join(CORPUS_PATH, 'emnet')
DATABASE_PATH = os.path.join(EMNET_PATH, "database.pkl")
INDEX_PATH = os.path.join(EMNET_PATH, "index.pkl")
model = None


# Search functions
def start_search(query_type: str, query: str):
    database = open_database()
    if query_type == 'By topic':
        query_embedding = model.encode([query])
        db_embeddings, db_docs = read_database(database)
    elif query_type == 'By file':
        query = f"{CORPUS_PATH}{os.sep}{query}"
        try:
            query_embedding = database[query]
        except:
            return 0
        del database[query]
        db_embeddings, db_docs = read_database(database)
    results = search_query(query_embedding, db_docs, db_embeddings)
    return results


def search_query(query_embedding, docs: list[str], embeddings: NDArray):
    similarities = torch.flatten(model.similarity(embeddings, query_embedding))
    match_values_tensor, match_indexes_tensor = torch.topk(similarities, k=5)
    match_values, match_indexes = match_values_tensor.tolist(), match_indexes_tensor.tolist()
    results = [(docs[index].split(os.sep)[-1],) for index in match_indexes]
    return results


# Document embedding & processing functions
def load_model():
    global model
    if model is None:
        model = SentenceTransformer('all-MiniLM-L6-v2')


def split_doc(full_doc: list[str]):
    doc_length = len(full_doc)
    doc_chunks = []
    chunk_len = 512
    chunks = doc_length // chunk_len
    leftover_chunk = doc_length % chunk_len
    for i in range(chunks):
        doc_chunks.append(' '.join(full_doc[i * chunk_len:(i + 1) * chunk_len]))
    if leftover_chunk:
        doc_chunks.append(' '.join(full_doc[(chunks*chunk_len):]))
    return doc_chunks


def pool_embeddings(embeddings: NDArray):
    embeddings_list = [*embeddings]
    pooled_embeddings = np.mean(embeddings_list, axis=0, keepdims=True)
    return pooled_embeddings


def embed_document(doc_path: str):
    with open(doc_path, 'r', encoding="utf-8") as document:
        full_doc = document.read().split()
        doc_chunks = split_doc(full_doc)
        embeddings = model.encode(doc_chunks)
        mean_embeddings = pool_embeddings(embeddings)
        return {doc_path: mean_embeddings}


def embed_corpus(docs: list[str]):
    corpus_embeddings = {name: embeddings for doc in docs for name, embeddings in embed_document(doc).items()}
    return corpus_embeddings


# Database functions
def create_database(current_index: list[str]):
    corpus_embeddings = embed_corpus(current_index)
    if not os.path.exists(EMNET_PATH):
        os.mkdir(EMNET_PATH)
    with open(DATABASE_PATH, 'wb') as database:
        pickle.dump(corpus_embeddings, database)
    cache_index(current_index)


def extend_database(docs_to_embed: list[str], current_index: list[str]):
    new_embeddings = embed_corpus(docs_to_embed)
    with open(DATABASE_PATH, 'rb') as database:
        db_dic = pickle.load(database)
    db_dic.update(new_embeddings)
    with open(DATABASE_PATH, 'wb') as database:
        pickle.dump(db_dic, database)
    cache_index(current_index)


def cache_index(current_index: list[str]):
    with open(INDEX_PATH, 'wb') as index:
        pickle.dump(current_index, index)


def initialize_database(current_index: list[str]):
    print('Checking for database...\n')
    if not os.path.exists(DATABASE_PATH):
        print('Creating database...\n')
        load_model()
        create_database(current_index)
    else:
        print('Loading database...\n')
        with open(INDEX_PATH, 'rb') as index:
            index_cache = pickle.load(index)
        if set(index_cache) != set(current_index):
            docs_to_embed = np.setdiff1d(current_index, index_cache).tolist()
            if docs_to_embed:
                answer = input('Update database? Y/N: ')
                if answer == 'Y':
                    print('\nUpdating database...')
                    load_model()
                    extend_database(docs_to_embed, current_index)


def open_database():
    with open(DATABASE_PATH, 'rb') as database:
        database = pickle.load(database)
    return database


def read_database(database: dict):
    db_embeddings = np.array([value[0] for value in database.values()])
    db_docs = [key for key in database.keys()]
    return db_embeddings, db_docs


# Others
def initialize_engine():
    current_index = glob.glob(f"{CORPUS_PATH}{os.sep}*.txt", recursive=True)
    initialize_database(current_index)

