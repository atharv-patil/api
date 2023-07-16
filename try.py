from collections import defaultdict
from flask import Flask, request, jsonify, Response
import pandas as pd
import numpy as np
import pickle
import json
import os
from pymongo import MongoClient

connection_string = f"mongodb+srv://woqalora:OMutKQ6FUT5g6jVa@project.bvqkqfy.mongodb.net/?retryWrites=true&w=majority"
client = MongoClient(connection_string)

user_ratings_db = client.books.user_ratings
read_list_db = client.books.read_list

app = Flask(__name__)

books_600_data = pd.read_csv("new.csv")
books_600_data["weighted_rating"] = np.nan


with open('matrix_clb_ftr.pkl', 'rb') as file:
    matrix_clb_ftr = pickle.load(file)

isbn_to_order = {}
with open("order_clb_ftr.txt", "r") as f:
    order_to_isbn = f.readlines()
for i in range(len(order_to_isbn)):
    order_to_isbn[i] = order_to_isbn[i].replace("\n", "")

for i in range(len(order_to_isbn)):
    isbn_to_order[order_to_isbn[i]] = i

# ----------------------------------------------------------------------------


@app.route('/get_order', methods=['POST'])
def collaborative_recommendations():
    try:
        global books_600_data
        data = request.get_json()
        userid = data["userid"]
        books_rated = user_ratings_db.find({"userid": userid})
        user_ratings = np.zeros((600,))
        s = set()
        for books in books_rated:
            isbn = books["isbn"]
            rating = books["rating"]
            try:
                rating = int(rating)
            except:
                rating = 0
            s.add(isbn)
            user_ratings[isbn_to_order[isbn]] = rating-2.5
        if len(s) == 0:
            json_str = books_600_data.to_json(orient='records')
            return Response(response=json_str, status=200, mimetype="application/json")

        result = np.dot(matrix_clb_ftr, user_ratings)
        mapper = [(result[i], i) for i in range(600)]
        mapper.sort(reverse=True)

        for i, j in mapper:
            if order_to_isbn[j] in s:
                i = 0
            books_600_data.loc[books_600_data["ISBN"] ==
                               order_to_isbn[j], "weighted_rating_temp"] = i

        books_600_data_temp = books_600_data.sort_values(
            by="weighted_rating_temp", ascending=False)

        df_without_rating = books_600_data_temp.drop(
            'weighted_rating_temp', axis=1)

        json_str = df_without_rating.to_json(orient='records')

        return Response(response=json_str, status=200, mimetype="application/json")

    except Exception as e:
        return jsonify({'error': str(e)})


# for readlist related operations


@app.route('/add_readbook', methods=['POST'])
def add_book():
    try:
        data = request.get_json()
        userid = data["userid"]
        ISBN = data["isbn"]

        existing_book = read_list_db.find_one(
            {"userid": userid, "isbn": ISBN})
        if existing_book:
            return Response("Book already exists in the read list.", status=400)

        read_list_db.insert_one(data)
        return jsonify({'status': "OK"})
    except Exception as e:
        print(f"Error: {e}")
        return Response(status=500)


@app.route('/list_readbooks', methods=['POST'])
def get_book_list():
    try:
        data = request.get_json()
        userid = data["userid"]
        books_added = read_list_db.find({"userid": userid})
        result = []
        for i in books_added:
            print(i)
            i.pop("_id")
            result.append(i)
        print(len(result))
        return jsonify(result)
    except Exception as e:
        print(f"Error: {e}")
        return Response(status=500)


@app.route('/delete_readbook', methods=['POST'])
def delete_book():
    try:
        data = request.get_json()
        userid = data["userid"]
        ISBN = data["isbn"]

        existing_book = read_list_db.find_one(
            {"userid": userid, "isbn": ISBN})
        if existing_book:
            read_list_db.delete_one({"userid": userid, "isbn": ISBN})
            return Response(status=200)
        else:
            return Response("Book not found in the read list.", status=404)
    except Exception as e:
        print(f"Error: {e}")
        return Response(status=500)

# for rating realted operations


@app.route('/insert_ratings', methods=['POST'])
def add():
    try:
        data = request.get_json()
        try:
            data["rating"] = int(data["rating"])
        except:
            data["rating"] = 0

        user_ratings_db.insert_one(data)

        return jsonify({'status': "OK"})
    except Exception as e:
        return jsonify({'error': str(e), "status": "NOT INSERTED"})


@app.route('/list_ratedbooks', methods=['POST'])
def get_list():
    try:
        data = request.get_json()
        userid = data["userid"]
        books_added = user_ratings_db.find({"userid": userid})

        result = []
        for i in books_added:
            i.pop("_id")
            result.append(i)

        return jsonify(result)
    except Exception as e:
        print(f"Error: {e}")
        return Response(status=500)


@app.route('/delete_ratedbook', methods=['POST'])
def delete():
    try:
        data = request.get_json()
        userid = data["userid"]
        ISBN = data["isbn"]

        existing_book = user_ratings_db.find_one(
            {"userid": userid, "isbn": ISBN})
        if existing_book:
            user_ratings_db.delete_one({"userid": userid, "isbn": ISBN})
            return Response(status=200)
        else:
            return Response("Book not found in the read list.", status=404)
    except Exception as e:
        print(f"Error: {e}")
        return Response(status=500)





if __name__ == "__main__":
    try:
        app.run(debug=True, port=5000)
    except Exception as e:
        print(f"Error: {e}")