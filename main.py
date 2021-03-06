import argparse
import csv, sys
from nltk import word_tokenize
from sentence_analysis import sentence_tagger, get_nodes, triples_extractor
import sys
from resources_loader import load_files
from resource_writer import update_resources
import pprint
from kb_query import distance_one_query, distance_two_query, get_evidence
from reasoner import evidence_writer, get_rule_predicates, clingo_map, inference_map, inference_prob, domain_generator,\
    rule_evidence_writer, inference_prob_mcsat, inference_map_weight
from ambiverse_api import ambiverse_entity_parser
import datetime


def fact_checker(sentence_lis, id_list, true_labels, data_source, input, pos_neg):
    true_count = 0
    false_count = 0
    true_pos = 0
    true_neg = 0
    rule_predicates, rules = get_rule_predicates(data_source)
    file_triples, ambiverse_resources = load_files(data_source)
    sentence_list = [word_tokenize(sent) for sent in sentence_lis]
    named_tags = sentence_tagger(sentence_list)
    lpmln_evaluation = [
        ['sentence_id', 'true_label', 'sentence', 'label', 'prediction', 'lpmln-prob', 'lpmln-map', 'clingo',
         'prob_all', \
         'clingo_all', 'map_all']]
    triple_flag = False
    ambiverse_flag = False
    for n, ne in enumerate(named_tags):
        sentence_id = id_list[n]
        true_label = true_labels[n]
        if not pos_neg:
            if true_label == 'T':
                true_count += 1
            else:
                false_count += 1
        else:
            if true_label == 'F':
                true_count += 1
            else:
                false_count += 1
        sentence_check = sentence_lis[n]
        print sentence_id, sentence_check, true_label, '\n'
        named_entities = get_nodes(ne)
        entity_dict = dict(named_entities)
        print "NER: " + str(entity_dict)
        if sentence_id in file_triples.keys():
            triple_dict = file_triples[sentence_id]
        else:
            triple_dict = triples_extractor(sentence_check, named_entities)
            if triple_dict:
                file_triples[sentence_id] = triple_dict
                triple_flag = True
        print "Relation Triples: " + str(triple_dict)
        if sentence_id in ambiverse_resources.keys():
            resource = ambiverse_resources[sentence_id]
        else:
            resource = ambiverse_entity_parser(sentence_check)
            ambiverse_resources[sentence_id] = resource
            ambiverse_flag = True
        print "Resource Extractor"
        print "=================="
        pprint.pprint(resource)
        for triples_k, triples_v in triple_dict.iteritems():
            for triple_v in triples_v:
                resource_v = [resource.get(trip_v).get('dbpedia_id') for trip_v in triple_v]
        print resource_v
        answer_all, answer_set, map, map_all, prob, label_prob = lpmln_reasoning(resource_v, rule_predicates, sentence_id,\
                                                                     data_source, rules, pos_neg)
        if not pos_neg:
            if true_label == 'T' and len(map) > 0:
                true_pos += 1
                prediction = 1
            elif true_label == 'F' and len(map) == 0:
                true_neg += 1
                prediction = 1
            else:
                prediction = 0
        else:
            if true_label == 'F' and len(map) > 0:
                true_pos += 1
                prediction = 1
            elif true_label == 'T' and len(map) == 0:
                true_neg += 1
                prediction = 1
            else:
                prediction = 0

        lpmln_evaluation.append(
            [sentence_id, true_label, sentence_check, label, str(prediction), str(prob), str(map), str(answer_set), \
             str(answer_all), str(map_all)])
    stats_computer(true_count, true_pos, false_count, true_neg, data_source)
    update_resources(triple_flag, ambiverse_flag, file_triples, ambiverse_resources, lpmln_evaluation, data_source, input)


def lpmln_reasoning(resource_v, rule_predicates, sentence_id, data_source, rules, rules_const, data_size, const, \
                    total_asp, total_map, total_mc, rule_type):
    query_evidence = True
    query_prob = False
    query_map = True

    resource_v = [entity.decode('utf-8') for entity in resource_v]
    # print resource_v

    if query_evidence:
        evidence = get_evidence(resource_v, rules)
        # for entity in resource_v:
        #     evidence = distance_one_query(entity, evidence)
        #     evidence = distance_two_query(entity, evidence)
    else:
        evidence = True

    if evidence:
        # print evidence
        if query_map:
            if query_evidence:
                evidence_set, entity_set = evidence_writer(evidence, sentence_id, data_source, resource_v, \
                                                           rule_predicates, rule_type)
            else:
                evidence_set = True
            if evidence_set:
                map, label_map, asp_time = inference_map(sentence_id, data_source, resource_v, data_size, const, rule_type)
                map_wt, label_map_wt, map_time = inference_map_weight(sentence_id, data_source, resource_v, data_size,\
                                                                      const, rule_type)
                total_asp += asp_time
                total_map += map_time
            else:
                map_wt, label_map_wt, map, label_map = 'NO_EVD', 'NO_EVD','NO_EVD', 'NO_EVD'
        else:
            map_wt, label_map_wt, map, label_map = '', '', '', ''

        if query_prob:
            if query_evidence:
                evidence_set, entity_set = rule_evidence_writer(evidence, sentence_id, data_source, resource_v, \
                                                            rule_predicates, rules, rules_const)
            else:
                evidence_set = True
            if evidence_set:
                domain_generator(entity_set, sentence_id, data_source)
                # prob, label_prob = inference_prob(sentence_id, data_source, resource_v)
                prob, label_prob, total_mc = inference_prob_mcsat(sentence_id, data_source, resource_v)
                # print prob, label_prob
            else:
                prob, label_prob = 'NO_EVD', 'NO_EVD'
        else:
            prob, label_prob = '',''

        return map_wt, label_map_wt, map, prob, label_prob, label_map, query_prob, query_map, total_asp, total_map, total_mc
    return '', '', '', '', '','', query_prob, query_map, total_asp, total_map, total_mc


def stats_computer(init_time, true_count, true_pos, false_count, true_neg, data_source, true_neutral, false_neutral, false_neg, \
                   false_pos, true_none, false_none,true_unsat,false_unsat, true_no_evd, false_no_evd, true_neutral_wt,\
                   false_neutral_wt, false_neg_wt, false_pos_wt, true_none_wt, false_none_wt, \
                   true_unsat_wt,false_unsat_wt, true_no_evd_wt, false_no_evd_wt, true_pos_wt, true_neg_wt, const, data_size):
    pre = 0
    rec = 0
    # false_neg = true_count-true_pos
    # false_pos = false_count - true_neg
    if true_count:
        tp = float(true_pos)/float(true_count)
    else:
        tp = 0
    if false_count:
        tn = float(true_neg)/float(false_count)
    else:
        tn = 0
    print "True Count:", true_count, "True Pos: ", true_pos, "=>", tp, "False Neg: ", false_neg
    if true_pos + false_pos > 0:
        pre = float(true_pos) / float(true_pos + false_pos)
    if true_pos + false_neg > 0:
        rec = float(true_pos) / float(true_pos + false_neg)

    # print "True Neutral: ", true_neutral
    # print "True UNSAT: ", true_unsat
    # print "True NO EVD+None: ", true_no_evd+true_none
    # print "True None: ", true_none
    # print "True NO EVD: ", true_no_evd
    #
    # print "False Count: ", false_count, "True Neg: ", true_neg, "=>", tn, "False Pos: ", false_pos
    # print "False Neutral: ", false_neutral
    # print "False UNSAT: ", false_unsat
    # print "False NO EVD+None: ", false_no_evd+false_none
    # print "False None: ", false_none
    # print "False NO EVD: ", false_no_evd
    #
    # print "----------------------------"
    #
    # print "True Count:", true_count, "True Pos_wt: ", true_pos_wt, "=>", tp, "False Neg_wt: ", false_neg_wt
    # print "True Neutral_wt: ", true_neutral_wt
    # print "True UNSAT_wt: ", true_unsat_wt
    # print "True NO EVD+None_wt: ", true_no_evd+true_none_wt
    # print "True None_wt: ", true_none_wt
    # print "True NO EVD_wt: ", true_no_evd_wt
    #
    # print "False Count_wt: ", false_count, "True Neg_wt: ", true_neg_wt, "=>", tn, "False Pos_wt: ", false_pos_wt
    # print "False Neutral_wt: ", false_neutral_wt
    # print "False UNSAT_wt: ", false_unsat_wt
    # print "False NO EVD+None_wt: ", false_no_evd+false_none_wt
    # print "False None_wt: ", false_none_wt
    # print "False NO EVD_wt: ", false_no_evd_wt

    st = datetime.datetime.now()
    print "Execution Time: ", (st-init_time).total_seconds()
    with open('dataset/' + data_source + '/output_stats/'+const+'_'+data_size+'_output.txt','a') as file:
        file.write(str(st))
        file.write("-------------------------------"+'\n')
        file.write("True Neutral: " + str(true_neutral) + '\n')
        file.write("False Neutral: " + str(false_neutral) + '\n')
        file.write("True None: " + str(true_none) + '\n')
        file.write("False None: " + str(false_none) + '\n')
        file.write("True UNSAT: " + str(true_unsat) + '\n')
        file.write("False UNSAT: " + str(false_unsat) + '\n')
        file.write("True NO EVD: " + str(true_no_evd) + '\n')
        file.write("False NO EVD: " + str(false_no_evd) + '\n')
        file.write("True Count:" + str(true_count) + " True Pos: " + str(true_pos) + " False Neg: " + \
                   str(false_neg) + '\n')
        file.write("False Count: " + str(false_count) + " True Neg: " + str(true_neg) + " False Pos: " +\
                   str(false_pos) + '\n')
        file.write("Execution Time: "+ str((st-init_time).total_seconds()))
        file.write('\n'+"-------------------------------")

    st_1 = datetime.datetime.now()
    print "Execution Time: ", (st_1-st).total_seconds()
    with open('dataset/' + data_source + '/output_stats/' +const+'_'+data_size+'_output.txt','a') as file:
        file.write(str(st))
        file.write("-------------------------------"+'\n')
        file.write("True Neutral_wt: " + str(true_neutral_wt) + '\n')
        file.write("False Neutral_wt: " + str(false_neutral_wt) + '\n')
        file.write("True None_wt: " + str(true_none_wt) + '\n')
        file.write("False None_wt: " + str(false_none_wt) + '\n')
        file.write("True UNSAT_wt: " + str(true_unsat_wt) + '\n')
        file.write("False UNSAT_wt: " + str(false_unsat_wt) + '\n')
        file.write("True NO EVD_wt: " + str(true_no_evd_wt) + '\n')
        file.write("False NO EVD+wt: " + str(false_no_evd_wt) + '\n')
        file.write("True Count:" + str(true_count) + " True Pos_wt: " + str(true_pos_wt) + " False Neg_wt: " + \
                   str(false_neg_wt) + '\n')
        file.write("False Count: " + str(false_count) + " True Neg_wt: " + str(true_neg_wt) + " False_Pos: " + \
                   str(false_pos_wt) + '\n')
        file.write("Execution Time: "+ str((st-init_time).total_seconds()))
        file.write('\n'+"-------------------------------")
    # true_data_pos = str(round(tp,2)) + ' ('+str(true_pos)+'/'+str(true_count)+')'
    # false_data_pos = str(round(1-tp,2)) + ' (' + str(false_neg)+'/'+str(true_count)+')'
    # true_data_neg = str(round(tn,2))+ ' ('+str(true_neg)+'/'+str(false_count)+')'
    # false_data_neg = str(round(1-tn,2))+' ('+str(false_pos)+'/'+str(false_count)+')'

    # output_stats = str(st) + ' ' + data_source + ' top-' + str(top_k) + ' & ' + true_data_pos + ' & ' + false_data_pos\
    #                + ' & ' + true_data_neg + ' & ' + false_data_neg + ' & ' + str(round(pre, 2)) + ' & ' + str(round(rec, 2))
    # with open('output_all.txt', 'a') as the_file:
    #     the_file.write(str(output_stats)+'\n')
    # print output_stats


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("-i", "--input", default='sentences_test.csv')
    parser.add_argument("-l", "--lpmln", default=False)
    parser.add_argument("-s", "--sentence", default='')
    parser.add_argument("-t", "--test_predicate", default='sample_case')
    parser.add_argument("-p", "--pos_neg", default='')
    args = parser.parse_args()
    with open('dataset/' + args.test_predicate + '/input/' + args.input) as f:
        reader = csv.DictReader(f)
        sentences_list = []
        id_list = []
        true_labels = []
        for row in reader:
            sentences_list.append(row.get('sentence'))
            true_labels.append(row.get('label'))
            id_list.append(row.get('id'))
        fact_checker(sentences_list, id_list, true_labels, args.test_predicate, args.input, args.pos_neg)
