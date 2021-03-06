import glob
import os
import scipy.io.wavfile as wav
import python_speech_features as pspeech
import numpy as np
import scipy.signal as sig
import shutil
import librosa

class CommonHelpers(object):

    def get_labels_and_count(self,label_file):

        """
        @type label_file:str
        :param label_file:
        :return:
        """

        print ('Label file is:'+ label_file)
        dict_labels = {}
        num_labels = 0
        with open (str(label_file),'r') as labelfile:
            data = labelfile.readlines()

            for line in data:
                num_labels = num_labels + 1
                dict_labels.update({int(line.split(':')[0].strip()) : line.split(':')[1].strip().lower()})

        return (num_labels, dict_labels)

    def reset_folder_make_new(self,file_dir):

        """
        @:type label_count: int
        :param file_dir:
        :param label_count: the label count
        :return:

        """

        version_out_dir = file_dir + 'batch/'

        # Make a new directory, if this is a new graph version, to store all the batches in there for the new graph version
        if (os.path.isdir(version_out_dir)):
            shutil.rmtree(version_out_dir)

        os.makedirs(version_out_dir)

        return version_out_dir



    def stamp_label(self,filename):

        l = int(filename.split('-')[1])
        return l

class InputRaw(object):

    def prepare_mfcc_spectogram(self,file_dir,file_name,ncep,nfft,cutoff_mfcc,cutoff_spectogram,mfcc_padding_value = 0,specto_padding_value = 0):


        fs,signal = wav.read(file_dir + file_name)
        mfcc = pspeech.mfcc(signal=signal,samplerate=fs,numcep=ncep)
        f, t, specgram = sig.spectrogram(x=signal,fs=fs,nfft=nfft)

        # Truncate mfcc frames to specified maximum cutoff
        if(mfcc.shape[0] > cutoff_mfcc):
                mfcc = mfcc[:cutoff_mfcc,:]

        # MFCC: Apply padding if frame length lower than cutoff
        mfcc_padding = ((0, cutoff_mfcc - mfcc.shape[0]), (0, 0))
        nparr_mfcc = np.pad(mfcc, pad_width=mfcc_padding, mode='constant', constant_values=mfcc_padding_value) # Pad the mfcc with the padding value

        # Spectogram padding
        specgram2 = specgram.transpose() # Time major
        if (specgram2.shape[0] > cutoff_spectogram):
            specgram2 = specgram2[:cutoff_spectogram,:]

        specgram_padding = ((0,cutoff_spectogram - specgram2.shape[0]),(0,0))
        nparr_specgram = np.pad(specgram2,pad_width=specgram_padding,mode='constant',constant_values=specto_padding_value) # Pad with input spectogram value

        return nparr_mfcc,nparr_specgram

    def prepare_log_mel_spectogram(self,file_dir,file_name,cutoff_mel_spectogram,padding_value=0):

        eps = 1e-10

        y, sr = librosa.load(file_dir + file_name, sr=None)
        ps = librosa.feature.melspectrogram(y = y, sr = sr)
        psnp = np.asarray(ps)

        mel_spgm = psnp.transpose() # Time major
        if (mel_spgm.shape[0] > cutoff_mel_spectogram):
            mel_spgm = mel_spgm[:cutoff_mel_spectogram,:]

        mel_padding = ((0,cutoff_mel_spectogram - mel_spgm.shape[0]),(0,0))
        mel_padded_spgm = np.pad(mel_spgm,mel_padding,mode='constant',constant_values=padding_value)
        log_mel_pad_spgm = np.log(mel_padded_spgm + eps)

        return log_mel_pad_spgm

    def create_numpy_batches(self,file_dir,batch_size,ncep,nfft,cutoff_mfcc,cutoff_spectogram,use_nfft):

        common_helpers = CommonHelpers()
        os.chdir(file_dir)
        version_out_dir = common_helpers.reset_folder_make_new(file_dir)

        os.makedirs(version_out_dir + 'inputs/')
        os.makedirs(version_out_dir + 'labels/')

        file_count = len([name for name in os.listdir('.') if os.path.isfile(name)])
        if (file_count == 0):
            print ('No files in the directory:' + file_dir + ' exiting now')
            raise Exception ('No files in the directory:' + file_dir)

        file_count -= 1

        i = 0
        inputs = []
        labels = []

        print ('Count of files in training directory' + file_dir + ' is: ' + str(file_count))
        print ('Preparing the numpy batches to the directory:' + version_out_dir)

        for file in glob.glob("*.wav"):

            mfcc,_ = self.prepare_mfcc_spectogram(file_dir = file_dir,file_name=file,ncep=ncep,nfft=nfft,cutoff_mfcc = cutoff_mfcc,
                                                           cutoff_spectogram=cutoff_spectogram)

            mel_spectogram = self.prepare_log_mel_spectogram(file_dir = file_dir, file_name= file ,cutoff_mel_spectogram=cutoff_spectogram)

            if (use_nfft):
                input_raw = mel_spectogram.tolist()

            else:
                input_raw = mfcc.tolist()

            inputs.append(input_raw)

            l = common_helpers.stamp_label(filename=file)
            labels.append(l)

            i = i + 1

            if (i % batch_size == 0 or i == file_count):

                npInputs = np.array(inputs)
                npLabels = np.array(labels)

                print (npInputs.shape)
                print (npLabels.shape)

                print ('Saving batch ' + str(i) + ' to the output dir ' + version_out_dir)
                # Numpy batch dump the voice files in batches of batch_size
                np.save(version_out_dir + 'inputs/models_numpy_batch' + '_' + str(i) + '.npy', npInputs)
                np.save(version_out_dir + 'labels/models_numpy_batch' + '_' + str(i) + '.npy', npLabels)
                inputs = []
                labels = []

        return version_out_dir, file_count


# Debugging
if (__name__ == '__main__'):

    vgg_chkpt = '/home/nitin/Desktop/aws_habits/FMSG_Habits/audioset/vggish_model.ckpt'
    labels_meta_file = '/home/nitin/Desktop/aws_habits/FMSG_Habits/habits/labels_meta/labels_meta.txt'

    in_dir = ''
    out_dir = '/home/nitin/Desktop/sdb1/all_files/tensorflow_voice/train_batch/'
    embed_dir = '/home/nitin/Desktop/sdb1/all_files/tensorflow_voice/train_embedding/'
    embed_batch_dir = '/home/nitin/Desktop/sdb1/all_files/tensorflow_voice/train_embedding/numpy_batch/'


    #inputs_vgg.generate_vggish_inputs(in_dir,out_dir)
    #inputs_vgg.generate_vggish_embeddings(out_dir,embed_dir)
    #inputs_vgg.generate_embeddings_batch(embed_dir, embed_batch_dir, 500)

    in_dir = '/home/nitin/Desktop/sdb1/all_files/tensorflow_voice/valid/'
    out_dir = '/home/nitin/Desktop/sdb1/all_files/tensorflow_voice/valid_batch/'
    embed_dir = '/home/nitin/Desktop/sdb1/all_files/tensorflow_voice/valid_embedding/'
    embed_batch_dir = '/home/nitin/Desktop/sdb1/all_files/tensorflow_voice/valid_embedding/numpy_batch/'


    #inputs_vgg.generate_vggish_inputs(in_dir, out_dir)
    #inputs_vgg.generate_vggish_embeddings(out_dir, embed_dir)
    #inputs_vgg.generate_embeddings_batch(embed_dir, embed_batch_dir, 500)

    in_dir = '/home/nitin/Desktop/sdb1/all_files/tensorflow_voice/test/'
    out_dir = '/home/nitin/Desktop/sdb1/all_files/tensorflow_voice/test_batch/'
    embed_dir = '/home/nitin/Desktop/sdb1/all_files/tensorflow_voice/test_embedding/'
    embed_batch_dir = '/home/nitin/Desktop/sdb1/all_files/tensorflow_voice/test_embedding/numpy_batch/'


    #inputs_vgg.generate_vggish_inputs(in_dir, out_dir)
    #inputs_vgg.generate_vggish_embeddings(out_dir, embed_dir)
    #inputs_vgg.generate_embeddings_batch(embed_dir, embed_batch_dir, 500)







