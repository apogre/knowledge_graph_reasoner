import argparse
import csv
import itertools
import random


def data_reader(folder_path,file_name):
    data_1 = []
    data_2 = []
    true_data = []
    with open(folder_path+file_name+".csv", 'rb') as resultFile:
        inputs = csv.DictReader(resultFile)
        for inp in inputs:
            print inp
            data_1.append(inp['sub'])
            data_2.append(inp['obj'])
            true_data.append((inp['sub'],inp['obj']))
    return data_1, data_2, true_data


def write_samples(folder_path, i, true_data, false_data,file_name):
    with open(folder_path+"sample_"+str(i)+file_name+".csv", 'wb') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(['sid', 'sub', 'obj', 'class'])
        j = 1
        for td in true_data:
            writer.writerow([j,td[0],td[1],1])
            j += 1
        for fd in false_data:
            writer.writerow([j,fd[0],fd[1],0])
            j += 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("-t", "--test_predicate", default='sample_case')
    args = parser.parse_args()
    folder_path = 'dataset/'+args.test_predicate+'/input/'
    file_name = 'positives_states'
    data_1, data_2, true_data = data_reader(folder_path,file_name)
    catesian_data = []

    true_sample = []
    for element in itertools.product(data_1, data_2):
        catesian_data.append(element)
    for i in range(3):
        false_data = []
        sample = random.sample(catesian_data, 60)
        for sam in sample:
            if sam not in true_data and len(false_data) < 50:
                false_data.append(sam)
            else:
                true_sample.append(sam)
        print "True", len(true_sample), true_sample
        print "False", len(false_data), false_data
        write_samples(folder_path, i, true_data, false_data,file_name)



