import os
import time
import numpy as np

from sklearn import preprocessing
from sklearn.metrics import accuracy_score

import sktime.contrib.rotation_forest.rotation_forest_dev as rf1
import sktime.contrib.rotation_forest.rotation_forest_reworked as rf2

def load_arff(file_path):
    with open(file_path) as f:
        for line in f:
            if line.strip():
                if "@data" in line.lower():
                    data_started = True
                    break

        dataset = np.loadtxt(f,delimiter=",")
    X = dataset[:,0:dataset.shape[1]-1]
    Y = dataset[:,dataset.shape[1]-1]
    return X,Y

reducedUCI=["bank","blood","breast-cancer-wisc-diag",
        "breast-tissue","cardiotocography-10clases",
        "conn-bench-sonar-mines-rocks","conn-bench-vowel-deterding",
        "ecoli","glass","hill-valley",
        "image-segmentation","ionosphere","iris","libras","magic",
        "miniboone",
        "oocytes_merluccius_nucleus_4d","oocytes_trisopterus_states_5b",
        "optical","ozone","page-blocks","parkinsons","pendigits",
        "planning","post-operative","ringnorm","seeds","spambase",
        "statlog-landsat","statlog-shuttle","statlog-vehicle","steel-plates",
        "synthetic-control","twonorm","vertebral-column-3clases",
        "wall-following","waveform-noise","wine-quality-white","yeast"]


def set_classifier(cls, resampleId):
    """
    Basic way of determining the classifier to build. To differentiate settings just and another elif. So, for example, if
    you wanted tuned TSF, you just pass TuneTSF and set up the tuning mechanism in the elif.
    This may well get superceded, it is just how e have always done it
    :param cls: String indicating which classifier you want
    :return: A classifier.
    """
    if cls.lower() == 'rotf1':
        return rf1.RotationForest()
    elif cls.lower() == 'rotf2':
        return rf2.RotationForestClassifier()



def run_experiment(problem_path, results_path, cls_name, dataset, classifier=None, resampleID=0, overwrite=False, format=".ts", train_file=False):
    """
    Method to run a basic experiment and write the results to files called testFold<resampleID>.csv and, if required,
    trainFold<resampleID>.csv.
    :param problem_path: Location of problem files, full path.
    :param results_path: Location of where to write results. Any required directories will be created
    :param cls_name: determines which classifier to use, as defined in set_classifier. This assumes predict_proba is
    implemented, to avoid predicting twice. May break some classifiers though
    :param dataset: Name of problem. Files must be  <problem_path>/<dataset>/<dataset>+"_TRAIN"+format, same for "_TEST"
    :param resampleID: Seed for resampling. If set to 0, the default train/test split from file is used. Also used in output file name.
    :param overwrite: if set to False, this will only build results if there is not a result file already present. If
    True, it will overwrite anything already there
    :param format: Valid formats are ".ts", ".arff" and ".long". For more info on format, see
    https://github.com/alan-turing-institute/sktime/blob/master/examples/Loading%20Data%20Examples.ipynb
    :param train_file: whether to generate train files or not. If true, it performs a 10xCV on the train and saves
    :return:
    """

    build_test = True
    if not overwrite:
        full_path = str(results_path)+"/"+str(cls_name)+"/Predictions/" + str(dataset) +"/testFold"+str(resampleID)+".csv"
        if os.path.exists(full_path):
            print(full_path+" Already exists and overwrite set to false, not building Test")
            build_test=False
        if train_file:
            full_path = str(results_path) + "/" + str(cls_name) + "/Predictions/" + str(dataset) + "/trainFold" + str(
                resampleID) + ".csv"
            if os.path.exists(full_path):
                print(full_path + " Already exists and overwrite set to false, not building Train")
                train_file = False
        if train_file == False and build_test ==False:
            return

    #Different cases: if resample files are present, use them
    file_name1= problem_path + dataset + '/' + dataset + str(resampleID) + '_TRAIN' + format
    file_name2= problem_path + dataset + '/' + dataset + str(resampleID) + '_TEST' + format
    if os.path.isfile(file_name1) and os.path.isfile(file_name2):
        trainX, trainY = load_arff(problem_path + dataset + '/' + dataset + str(resampleID) + '_TRAIN' + format)
        testX, testY = load_arff(problem_path + dataset + '/' + dataset + str(resampleID) + '_TEST' + format)
        print("LOADING RESAMPLE FROM FILE")
    else: #Resample : CODE TO CHANGE: George implementing stratification by train distribution
        trainX, trainY = load_arff(problem_path + dataset + '/' + dataset + '_TRAIN' + format)
        testX, testY = load_arff(problem_path + dataset + '/' + dataset + '_TEST' + format)
        if resampleID !=0:
            # allLabels = np.concatenate((trainY, testY), axis = None)
            # allData = pd.concat([trainX, testX])
            # train_size = len(trainY) / (len(trainY) + len(testY))
            # trainX, testX, trainY, testY = train_test_split(allData, allLabels, train_size=train_size,
            #                                                                random_state=resampleID, shuffle=True,
            #                                                                stratify=allLabels)
            trainX, trainY, testX, testY = stratified_resample(trainX, trainY, testX, testY, resampleID)


    le = preprocessing.LabelEncoder()
    le.fit(trainY)
    trainY = le.transform(trainY)
    testY = le.transform(testY)
    if classifier is None:
        classifier = set_classifier(cls_name, resampleID)
    print(cls_name + " on " + dataset + " resample number " + str(resampleID))
    if build_test:
        # TO DO : use sklearn CV
        start = int(round(time.time() * 1000))
        classifier.fit(trainX,trainY)
        build_time = int(round(time.time() * 1000))-start
        start =  int(round(time.time() * 1000))
        probs = classifier.predict_proba(testX)
        preds = classifier.classes_[np.argmax(probs, axis=1)]
        test_time = int(round(time.time() * 1000))-start
        ac = accuracy_score(testY, preds)
        print(cls_name + " on " + dataset + " resample number " + str(resampleID) + ' test acc: ' + str(ac)
              + ' time: ' + str(test_time))
        #        print(str(classifier.findEnsembleTrainAcc(trainX, trainY)))
        if "Composite" in cls_name:
            second="Para info too long!"
        else:
            second = str(classifier.get_params())
        second.replace('\n',' ')
        second.replace('\r',' ')

        print(second)
        temp=np.array_repr(classifier.classes_).replace('\n', '')

        third = str(ac)+","+str(build_time)+","+str(test_time)+",-1,-1,"+str(len(classifier.classes_))
        write_results_to_uea_format(second_line=second, third_line=third, output_path=results_path, classifier_name=cls_name, resample_seed= resampleID,
                                predicted_class_vals=preds, actual_probas=probs, dataset_name=dataset, actual_class_vals=testY, split='TEST')
    if train_file:
        start = int(round(time.time() * 1000))
        if build_test and hasattr(classifier,"get_train_probs"):    #Normally Can only do this if test has been built ... well not necessarily true, but will do for now
            train_probs = classifier.get_train_probs(trainX)
        else:
            train_probs = cross_val_predict(classifier, X=trainX, y=trainY, cv=10, method='predict_proba')
        train_time = int(round(time.time() * 1000)) - start
        train_preds = classifier.classes_[np.argmax(train_probs, axis=1)]
        train_acc = accuracy_score(trainY,train_preds)
        print(cls_name + " on " + dataset + " resample number " + str(resampleID) + ' train acc: ' + str(train_acc)
              + ' time: ' + str(train_time))
        if "Composite" in cls_name:
            second="Para info too long!"
        else:
            second = str(classifier.get_params())
        second.replace('\n',' ')
        second.replace('\r',' ')
        temp=np.array_repr(classifier.classes_).replace('\n', '')
        third = str(train_acc)+","+str(train_time)+",-1,-1,-1,"+str(len(classifier.classes_))
        write_results_to_uea_format(second_line=second, third_line=third, output_path=results_path, classifier_name=cls_name, resample_seed= resampleID,
                                    predicted_class_vals=train_preds, actual_probas=train_probs, dataset_name=dataset, actual_class_vals=trainY, split='TRAIN')


def write_results_to_uea_format(output_path, classifier_name, dataset_name, actual_class_vals,
                                predicted_class_vals, split='TEST', resample_seed=0, actual_probas=None, second_line="No Parameter Info",third_line="N/A",class_labels=None):
    """
    This is very alpha and I will probably completely change the structure once train fold is sorted, as that internally
    does all this I think!
    Output mirrors that produced by this Java
    https://github.com/TonyBagnall/uea-tsc/blob/master/src/main/java/experiments/Experiments.java
    :param output_path:
    :param classifier_name:
    :param dataset_name:
    :param actual_class_vals:
    :param predicted_class_vals:
    :param split:
    :param resample_seed:
    :param actual_probas:
    :param second_line:
    :param third_line:
    :param class_labels:
    :return:
    """
    if len(actual_class_vals) != len(predicted_class_vals):
        raise IndexError("The number of predicted class values is not the same as the number of actual class values")

    try:
        os.makedirs(str(output_path)+"/"+str(classifier_name)+"/Predictions/" + str(dataset_name) + "/")
    except os.error:
        pass  # raises os.error if path already exists

    if split == 'TRAIN' or split == 'train':
        train_or_test = "train"
    elif split == 'TEST' or split == 'test':
        train_or_test = "test"
    else:
        raise ValueError("Unknown 'split' value - should be TRAIN/train or TEST/test")

    file = open(str(output_path)+"/"+str(classifier_name)+"/Predictions/" + str(dataset_name) +
                "/"+str(train_or_test)+"Fold"+str(resample_seed)+".csv", "w")

    # print(classifier_name+" on "+dataset_name+" for resample "+str(resample_seed)+"   "+train_or_test+" data has line three "+third_line)
    # the first line of the output file is in the form of:
    # <classifierName>,<datasetName>,<train/test>,<Class Labels>
    file.write(str(dataset_name) + ","+str(classifier_name)+"," + str(train_or_test)+","+str(resample_seed)+",MILLISECONDS,PREDICTIONS, Generated by experiments.py")
    file.write("\n")

    # the second line of the output is free form and classifier-specific; usually this will record info
    # such as parameter options used, any constituent model names for ensembles, etc.
    file.write(str(second_line)+"\n")

    # the third line of the file is the accuracy (should be between 0 and 1 inclusive). If this is a train
    # output file then it will be a training estimate of the classifier on the training data only (e.g.
    # 10-fold cv, leave-one-out cv, etc.). If this is a test output file, it should be the output
    # of the estimator on the test data (likely trained on the training data for a-priori parameter optimisation)
    file.write(str(third_line))
    file.write("\n")


    # from line 4 onwards each line should include the actual and predicted class labels (comma-separated). If
    # present, for each case, the probabilities of predicting every class value for this case should also be
    # appended to the line (a space is also included between the predicted value and the predict_proba). E.g.:
    #
    # if predict_proba data IS provided for case i:
    #   actual_class_val[i], predicted_class_val[i],,prob_class_0[i],prob_class_1[i],...,prob_class_c[i]
    #
    # if predict_proba data IS NOT provided for case i:
    #   actual_class_val[i], predicted_class_val[i]
    for i in range(0, len(predicted_class_vals)):
        file.write(str(actual_class_vals[i]) + "," + str(predicted_class_vals[i]))
        if actual_probas is not None:
            file.write(",")
            for j in actual_probas[i]:
                file.write("," + str(j))
            file.write("\n")

    file.close()





if __name__ == "__main__":
    """
    Debug testing for two RotationForest variants
    """
    print("Debug testing for Rotation Forest variants")
    classifier = "ROTF2"
    data_dir = 'E:/Data/UCI/'
    results_dir="E:/Temp/Python/"

    for i in range(0, len(reducedUCI)):
        dataset = reducedUCI[i]
        print(i)
        print(" problem = "+dataset)
        tf=False
        run_experiment(overwrite=False, problem_path=data_dir, results_path=results_dir, cls_name=classifier,
                       dataset=dataset, resampleID=0,train_file=tf,format=".arff")