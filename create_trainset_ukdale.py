# 用来将格式为.dat类型的UKDALE数据集，划分为训练集、验证集和测试集

from ukdale_parameters import *
import pandas as pd
import matplotlib.pyplot as plt
import time
import argparse
# from functions import load_dataframe

import pandas as pd


def load_dataframe(directory, building, channel, col_names=['time', 'data'], nrows=None):
    df = pd.read_table(directory + 'house_' + str(building) + '/' + 'channel_' +
                       str(channel) + '.dat',
                       sep="\s+",
                       nrows=nrows,
                       usecols=[0, 1],
                       names=col_names,
                       dtype={'time': str},
                       )
    return df
# kettle,  microwave, fridge, dishwasher, washingmachine
appliance_name = 'fridge'

DATA_DIRECTORY = 'D:/NILM_data/UKDALE/dat/'     
SAVE_PATH = 'D:/NILM_data/UKDALE/csv/ukdale_6s/'+appliance_name+'/'       #
AGG_MEAN = 522
AGG_STD = 814


def get_arguments():
    parser = argparse.ArgumentParser(description='sequence to point learning \
                                     example for NILM')
    parser.add_argument('--data_dir', type=str, default=DATA_DIRECTORY,
                          help='The directory containing the UKDALE data')

    parser.add_argument('--appliance_name', type=str, default=appliance_name,            
                          help='which appliance you want to train: kettle,\
                          microwave,fridge,dishwasher,washingmachine')
    parser.add_argument('--aggregate_mean', type=int, default=AGG_MEAN,
                        help='Mean value of aggregated reading (mains)')
    parser.add_argument('--aggregate_std', type=int, default=AGG_STD,
                        help='Std value of aggregated reading (mains)')
    parser.add_argument('--save_path', type=str, default=SAVE_PATH,
                          help='The directory to store the training data')
    return parser.parse_args()


args = get_arguments()
args.appliance_name = appliance_name
print(appliance_name)


def main():

    start_time = time.time()
    sample_seconds = 6                                #
    training_building_percent = 80                  #
    validation_percent = 20                         #
    nrows = None
    debug = False

    # val = pd.DataFrame(columns=['time','aggregate', appliance_name])        #
    # train = pd.DataFrame(columns=['time', 'aggregate', appliance_name])     #
    val = pd.DataFrame(columns=['aggregate', appliance_name])        
    train = pd.DataFrame(columns=[ 'aggregate', appliance_name])

    for h in params_appliance[appliance_name]['houses']:
        print('    ' + args.data_dir + 'house_' + str(h) + '/'
              + 'channel_' +
              str(params_appliance[appliance_name]['channels'][params_appliance[appliance_name]['houses'].index(h)]) +
              '.dat')

        mains_df = load_dataframe(args.data_dir, h, 1)
        app_df = load_dataframe(args.data_dir,
                                h,
                                params_appliance[appliance_name]['channels'][params_appliance[appliance_name]['houses'].index(h)],
                                col_names=['time', appliance_name]
                                )

        mains_df['time'] = pd.to_datetime(mains_df['time'], unit='s')
        mains_df.set_index('time', inplace=True)
        mains_df.columns = ['aggregate']
        #resample = mains_df.resample(str(sample_seconds) + 'S').mean()
        mains_df.reset_index(inplace=True)

        if debug:
            print("    mains_df:")
            print(mains_df.head())
            plt.plot(mains_df['time'], mains_df['aggregate'])
            plt.show()

        # Appliance
        app_df['time'] = pd.to_datetime(app_df['time'], unit='s')

        if debug:
            print("app_df:")
            print(app_df.head())
            plt.plot(app_df['time'], app_df[appliance_name])
            plt.show()

        # the timestamps of mains and appliance are not the same, we need to align them
        # 1. join the aggragte and appliance dataframes;
        # 2. interpolate the missing values;
        mains_df.set_index('time', inplace=True)
        app_df.set_index('time', inplace=True)

        df_align = mains_df.join(app_df, how='outer'). \
            resample(str(sample_seconds) + 'S').mean().fillna(method='backfill', limit=1)
        df_align = df_align.dropna()

        df_align.reset_index(inplace=True)

        # 是否保留时间戳
        del mains_df, app_df, df_align['time']
        # del mains_df, app_df

        if debug:
            # plot the dtaset
            print("df_align:")
            print(df_align.head())
            plt.plot(df_align['aggregate'].values)
            plt.plot(df_align[appliance_name].values)
            plt.show()

        # Normilization ----------------------------------------------------------------------------------------------
        mean = params_appliance[appliance_name]['mean']
        std = params_appliance[appliance_name]['std']

        df_align['aggregate'] = (df_align['aggregate'] - args.aggregate_mean) / args.aggregate_std
        df_align[appliance_name] = (df_align[appliance_name] - mean) / std
        #  Test CSV
        if h == params_appliance[appliance_name]['test_build']:
            df_align[appliance_name][df_align[appliance_name]>df_align['aggregate']] = df_align['aggregate'][df_align[appliance_name]>df_align['aggregate']]
            df_align.to_csv(args.save_path + appliance_name + '_test_.csv', mode='a', index=False, header=False)
            print("    Size of test set is {:.4f} M rows.".format(len(df_align) / 10 ** 6))
            continue
        
        val_len = int((len(df_align)/100)*validation_percent)
        val = val._append(df_align[-val_len:],  ignore_index=True)
        train = train._append(df_align[:-val_len],  ignore_index=True)

        # train = train.append(df_align, ignore_index=True)
        del df_align

    # Crop dataset
    # if training_building_percent is not 0:
    #     train.drop(train.index[-int((len(train)/100)*training_building_percent):], inplace=True)


    # Validation CSV
    # val_len = int((len(train)/100)*validation_percent)
    # val = train.tail(val_len)
    # val.reset_index(drop=True, inplace=True)
    # train.drop(train.index[-val_len:], inplace=True)
    # Validation CSV
    val[appliance_name][val[appliance_name]>val['aggregate']] = val['aggregate'][val[appliance_name]>val['aggregate']]
    train[appliance_name][train[appliance_name]>train['aggregate']] = train['aggregate'][train[appliance_name]>train['aggregate']]

    val.to_csv(args.save_path + appliance_name + '_validation_' + '.csv', mode='a', index=False, header=False)

    # Training CSV
    train.to_csv(args.save_path + appliance_name + '_training_.csv', mode='a', index=False, header=False)

    print("    Size of total training set is {:.4f} M rows.".format(len(train) / 10 ** 6))
    print("    Size of total validation set is {:.4f} M rows.".format(len(val) / 10 ** 6))
    del train, val


    print("\nPlease find files in: " + args.save_path)
    print("Total elapsed time: {:.2f} min.".format((time.time() - start_time) / 60))


if __name__ == '__main__':
    main()