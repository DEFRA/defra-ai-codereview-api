- brew install mongosh
- example connection to run: `mongosh mongodb://root:example@localhost:27017/code_reviews?authSource=admin" --eval 'db.classifications.find().toArray()'`