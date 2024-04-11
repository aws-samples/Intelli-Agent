import { apiRequest } from 'utils/request';

export const getLibraryList = async (params: {
  pageNumber: number;
  pageSize: number;
}) => {
  const result: any = await apiRequest('get', '/library', params);
  return result;
};
