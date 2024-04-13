import Axios from 'axios';

export const axios = Axios.create({
  timeout: 100000,
});
