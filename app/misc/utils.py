import math
import numpy as np
import scipy.special
import time


class Utils():

    @staticmethod
    def get_traceback(e, msg):
        traceback_str = ''
        traceback_str += f'{msg}: {type(e).__name__} due to "{e}"\n'

        tb_curr = e.__traceback__
        while tb_curr != None:
            traceback_str += f'    File "{tb_curr.tb_frame.f_code.co_filename}", line {tb_curr.tb_lineno} in {tb_curr.tb_frame.f_code.co_name}\n'
            tb_curr = tb_curr.tb_next

        return traceback_str


    @staticmethod
    def benchmark(cls_name):
        def decorator(func):
            def wrap_func(*args, **kwargs):
                t1 = time.perf_counter()
                result = func(*args, **kwargs)
                t2 = time.perf_counter()

                print(f'    | {cls_name}.{func.__name__} executed in {1000*(t2 - t1):.2f} ms')
                return result

            return wrap_func

        return decorator

    
    @staticmethod
    def profile(num, func, *args, **kwargs):
        data = []

        for _ in range(num):
            t1 = time.perf_counter()
            func(*args, **kwargs)
            data.append(time.perf_counter() - t1)

        print(f'{func.__name__} done in {1000*np.mean(data):.2f} ± {1000*2*np.std(data):.2f} ms')


class MathUtils():

    class PoiBin():
        
        def __init__(self, probs):
            omega = 2 * np.pi / (len(probs) + 1)

            half_number_trials = int(len(probs) / 2 + len(probs) % 2)
            num_values = min(250, half_number_trials)

            idx_array = np.arange(1, num_values + 1)
            exp_value = np.exp(omega * idx_array * 1j)

            # Multiplying each probability by each complex number forming an arc of a circle
            xy = 1 - probs + probs*exp_value.reshape(num_values, 1)
            
            argz_sum = np.arctan2(xy.imag, xy.real).sum(axis=1)

            d_value = np.zeros(num_values)
            d_value = np.abs(xy).prod(axis=1)

            chi = np.zeros(len(probs) + 1, dtype=complex)
            chi[0] = 1
            chi[1:num_values + 1] = d_value*np.exp(argz_sum * 1j)
            chi[half_number_trials + 1:len(probs) + 1] = np.conjugate(chi[1:len(probs) - half_number_trials + 1] [::-1])
            chi /= len(probs) + 1

            self.pmf = np.fft.fft(chi).real
            # self.cmf = np.add.accumulate(self.pmf)


        def pdf(self, x):
            return self.pmf[x]


        # def cdf(self, x):
        #     return self.cmf[x]


    @staticmethod
    def max_rolling(a, window, axis=1):
        # Thanks https://stackoverflow.com/a/52219082
        shape = a.shape[:-1] + (a.shape[-1] - window + 1, window)
        strides = a.strides + (a.strides[-1],)
        rolling = np.lib.stride_tricks.as_strided(a, shape=shape, strides=strides)
        return np.max(rolling, axis=axis)


    @staticmethod
    def normal_distr(x, avg, std):
        return 1/(std*((2*math.pi)**0.5))*np.exp(-0.5*((x - avg)/std)**2)


    @staticmethod
    def get_freq_hist(data):
        freq = np.zeros(data.shape[0])
        unique = np.unique(data)

        for val in unique:
            val_filter = (data == val)
            freq[val_filter] = np.arange(freq[val_filter].shape[0])

        return freq


    @staticmethod
    def calc_err(x_data, y_data, r, t_min, y=0):
        curve_fit = MathUtils.softplus_func(x_data, r, t_min, y)
        return np.sum(np.abs(y_data - curve_fit))


    @staticmethod
    def softplus_func(t, r, t_min, y=0):
        lin = r*(t - t_min)
        lin[lin < 100] = np.log(np.exp(lin[lin < 100]) + np.exp(y))
        return lin

    
    @staticmethod
    def linear_regresion(x, y):
        # Model processing. Needs at least 2 points.
        if y.shape[0] < 2:
            return None, None

        # Split data in half on x-axis and figure out if the data is increasing or decreasing
        left_half = x < np.median(x)
        right_half = x >= np.median(x)

        # If one of halves is empty, return None
        if not (any(left_half) and any(right_half)):
            return None, None

        y_left_avg = np.mean(y[x < np.median(x)])
        y_right_avg = np.mean(y[x >= np.median(x)])

        # Model linear curve
        # Visual example of how this works: https://i.imgur.com/k7H8bLe.png
        # 1) Take points on y-axis and x-axis, and split them into half - resulting in two groups
        avg_x = np.mean(x)
        avg_y = np.mean(y)

        if y_left_avg < y_right_avg:
            # Positive slope
            g1 = (x < avg_x) & (y < avg_y)    # Group 1 select
            g2 = (x >= avg_x) & (y >= avg_y)  # Group 2 select
        else:
            # Negative slope
            g1 = (x < avg_x) & (y >= avg_y)   # Group 1 select
            g2 = (x >= avg_x) & (y < avg_y)   # Group 2 select
        
        # Check if follows model by having positive linear slope
        if(not any(g1) or not any(g2)):
            return None, None

        # 2) Take the center of gravity for each of the two groups
        #    Those become points p1 and p2 to fit a line through
        p1x = np.mean(x[g1])
        p1y = np.mean(y[g1])

        p2x = np.mean(x[g2])
        p2y = np.mean(y[g2])

        # 3) Calculate slope and y-intercept
        m = (p1y - p2y)/(p1x - p2x)
        b = p1y - m*p1x

        return m, b
