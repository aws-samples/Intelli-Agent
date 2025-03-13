import {
  Container,
  Header,
  SpaceBetween,
  Button,
  StatusIndicator,
  Popover,
  ContentLayout,
} from '@cloudscape-design/components';
import CommonLayout from 'src/layout/CommonLayout';
import React, { useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import { LibraryExecutionItem, LibraryExecutionResponse } from 'src/types';
import { alertMsg, formatTime } from 'src/utils/utils';
import useAxiosRequest from 'src/hooks/useAxiosRequest';
import { useTranslation } from 'react-i18next';
import { ROUTES } from 'src/utils/const';

const LibraryDetail: React.FC = () => {
  const [loadingData, setLoadingData] = useState(false);
  const [executionFileList, setExecutionFileList] = useState<
    LibraryExecutionItem[]
  >([]);
  const fetchData = useAxiosRequest();
  const { t } = useTranslation();
  const { id } = useParams();

  const getLibraryDetail = async () => {
    setLoadingData(true);
    try {
      const data: LibraryExecutionResponse = await fetchData({
        url: `knowledge-base/executions/${id}`,
        method: 'get',
      });
      const executionRes: LibraryExecutionResponse = data;
      setExecutionFileList(executionRes.Items);
      setLoadingData(false);
    } catch (error: unknown) {
      setLoadingData(false);
      if (error instanceof Error) {
        alertMsg(error.message);
      }
    }
  };

  const getLibraryPrefix = (s3Path: string) => {
    if (!s3Path) return 'N/A';
    const lastSlashIndex = s3Path.lastIndexOf('/');
    const truncatedPath = s3Path.substring(0, lastSlashIndex);
    return truncatedPath;
  };

  const showIngestStatus = (status: string) => {
    if (status === 'FAILED') {
      return 'error';
    } else if (status === 'RUNNING') {
      return 'loading';
    } else {
      return 'success';
    }
  };

  useEffect(() => {
    getLibraryDetail();
  }, []);

  return (
    <CommonLayout
      isLoading={loadingData}
      activeHref={ROUTES.Library}
      breadCrumbs={[
        {
          text: t('name'),
          href: ROUTES.Home,
        },
        {
          text: t('docLibrary'),
          href: ROUTES.Library,
        },
        {
          text: `${id}`,
          href: '/detail',
        },
      ]}
    >
      <ContentLayout>
        <Container
          variant="default"
          header={
            <Header variant="h2" description={t('executionDetailDesc')}>
              {t('executionDetail')}
            </Header>
          }
        >
          <SpaceBetween direction="vertical" size="xs">
            <div className="flex align-center gap-10">
              {t('prefix')}:{' '}
              <b>{`${getLibraryPrefix(executionFileList?.[0]?.s3Path)}`} </b>
            </div>
            <div className="mt-10"></div>
            {executionFileList.length > 0 ? (
              executionFileList.map((item) => (
                <div className="flex align-center" key={item.s3Prefix}>
                  <StatusIndicator type={showIngestStatus(item.status)}>
                    [{formatTime(item.createTime)}] {item.s3Prefix}
                  </StatusIndicator>
                  {item.status === 'FAILED' && (
                    <Popover
                      dismissButton={false}
                      position="top"
                      size="large"
                      triggerType="custom"
                      content={
                        <StatusIndicator type="error">
                          {item.detail}
                        </StatusIndicator>
                      }
                    >
                      <Button iconName="status-info" variant="icon" />
                    </Popover>
                  )}
                </div>
              ))
            ) : (
              <div>{t('detailNoFiles')}</div>
            )}
          </SpaceBetween>
        </Container>
      </ContentLayout>
    </CommonLayout>
  );
};

export default LibraryDetail;
