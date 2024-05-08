import {
  BreadcrumbGroup,
  Container,
  Header,
  SpaceBetween,
  Button,
  StatusIndicator,
  Popover,
  ContentLayout,
} from '@cloudscape-design/components';
import CommonLayout from 'src/layout/CommonLayout';
import React, { useContext, useEffect, useState } from 'react';
import { axios } from 'src/utils/request';
import ConfigContext from 'src/context/config-context';
import { useParams } from 'react-router-dom';
import { LibraryExecutionItem, LibraryExecutionResponse } from 'src/types';
import { alertMsg, formatTime } from 'src/utils/utils';

const LibraryDetail: React.FC = () => {
  const [loadingData, setLoadingData] = useState(false);
  const [executionFileList, setExecutionFileList] = useState<
    LibraryExecutionItem[]
  >([]);
  const config = useContext(ConfigContext);
  const { id } = useParams();

  const getLibraryDetail = async () => {
    setLoadingData(true);
    const params = {
      executionId: id,
    };
    try {
      const result = await axios.get(`${config?.apiUrl}/etl/execution`, {
        params,
      });
      const executionRes: LibraryExecutionResponse = result.data;
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

  useEffect(() => {
    getLibraryDetail();
  }, []);

  return (
    <CommonLayout
      isLoading={loadingData}
      activeHref="/library"
      breadCrumbs={
        <BreadcrumbGroup
          items={[
            {
              text: 'AWS LLM Bot',
              href: '/',
            },
            {
              text: 'Docs Library',
              href: '/library',
            },
            {
              text: `${id}`,
              href: '/detail',
            },
          ]}
        />
      }
    >
      <ContentLayout>
        <Container
          variant="default"
          header={
            <Header
              variant="h2"
              description="Please check the file list below, and click the info icon for more details."
            >
              {`Execution detail`}
            </Header>
          }
        >
          <SpaceBetween direction="vertical" size="xs">
            <div className="flex align-center gap-10">
              ID: <b>{`${id}`} </b>
            </div>
            <div className="flex align-center gap-10">
              Prefix:{' '}
              <b>{`${getLibraryPrefix(executionFileList?.[0]?.s3Path)}`} </b>
            </div>
            <div className="mt-10"></div>
            {executionFileList.length > 0 ? (
              executionFileList.map((item) => (
                <div className="flex align-center" key={item.s3Prefix}>
                  <StatusIndicator
                    type={item.status === 'FAILED' ? 'error' : 'success'}
                  >
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
              <div>No files or please waiting execution to complete</div>
            )}
          </SpaceBetween>
        </Container>
      </ContentLayout>
    </CommonLayout>
  );
};

export default LibraryDetail;
