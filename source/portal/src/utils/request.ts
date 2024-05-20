import Axios from 'axios';

const axios = Axios.create({
  timeout: 100000,
});

export { axios };
