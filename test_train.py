# -*- coding: utf-8 -*-

import sparql
from config import sparql_dbpedia
import argparse
import csv
import sys

sparql_endpoint = sparql_dbpedia

def get_query(subject, object, relation, v):
    suffix = "} ORDER BY RAND() LIMIT " + str(v)
    print "Executing negative candidate query selection"
    prefix = "PREFIX dbpedia-owl: <http://dbpedia.org/ontology/> PREFIX dbp: <http://dbpedia.org/property/> PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> " \
             "SELECT DISTINCT ?subject ?object FROM <http://dbpedia.org> " \
             "WHERE { ?object rdf:type dbpedia-owl:"+object+". " \
             "?subject rdf:type dbpedia-owl:"+subject+". "

    negative_query = prefix + " {{?subject ?targetRelation ?realObject.} UNION  {?realSubject ?targetRelation ?object.}} " \
                              "?subject ?otherRelation ?object. " \
                              "FILTER (?targetRelation = dbpedia-owl:"+relation+") " \
                              "FILTER (?otherRelation != dbpedia-owl:"+relation+") " \
                              "FILTER NOT EXISTS {?subject dbpedia-owl:"+relation+" ?object.} " + suffix
    print negative_query

    print "Executing positive candidate query selection"

    positive_query = prefix + " ?subject ?targetRelation ?object.   " \
                              "FILTER (?targetRelation = dbpedia-owl:"+relation+") " + suffix
    print positive_query
    return positive_query, negative_query


def get_examples(query):
    print "Processing Examples"
    examples = []
    try:
        result = sparql.query(sparql_endpoint, query)
        examples = [sparql.unpack_row(row_result) for row_result in result]
        examples = [map(lambda x:x.split('/')[-1].encode('utf-8'), vals) for vals in examples]
    except Exception as e:
        print(e)
    if examples:
        size = len(examples)
        # train_size = size / 5
        return examples[:200], examples[200:]
        # return [], examples
    else:
        print "Examples Not Found"
    return [], []


def write_examples(folder_path, file_name, examples, k):
    with open(folder_path+file_name+"_"+k+".csv", 'wb') as resultFile:
        wr = csv.writer(resultFile,quotechar='"')
        wr.writerows(examples)


if __name__ == "__main__":
    # parser = argparse.ArgumentParser()
    # parser.add_argument("-t", "--test_predicate", default='spouse')
    # parser.add_argument("-s", "--subject", default='Person')
    # parser.add_argument("-o", "--object", default='Person')
    # args = parser.parse_args()
    # folder_path = 'dataset/'+args.test_predicate+'/input/'
    # data_size = {'1k':1000, '5k':5000, '10k':10000}
    data_size = {'10k': 10000}
    # positive_query, negative_query = get_query(args.subject, args.object,args.test_predicate)

    with open('dataset/dataset_lpmln.csv','rb')as datainput:
        reader = csv.DictReader(datainput)
        for row in reader:
            subject = row.get('subject')
            test_predicate = row.get('predicate')
            object = row.get('object')
            print "----------------------"
            print subject, test_predicate, object
            print "----------------------"
            folder_path = 'dataset/' + test_predicate + '/input/'
            for k,v in data_size.iteritems():
                print "query for",k,v
                positive_query, negative_query = get_query(subject, object, test_predicate, v)

                positive_test, positive_train = get_examples(positive_query)
                positive_test = [[i+1]+pos_test +[1] for i,pos_test in enumerate(positive_test)]

                negative_test, negative_train = get_examples(negative_query)
                negative_test = [[i+201]+neg_test + [0] for i,neg_test in enumerate(negative_test)]

                file_names = {'positive_examples':positive_train, 'negative_examples': negative_train, \
                              'test':positive_test+negative_test}
                for file_name,examples in file_names.iteritems():
                    print "writing", file_name
                    write_examples(folder_path, file_name, examples, k)