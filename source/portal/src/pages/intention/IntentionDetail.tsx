import {
  Container,
  Header,
  SpaceBetween,
  Button,
  StatusIndicator,
  Popover,
  ContentLayout,
  Box,
  TextFilter,
  Pagination,
  CollectionPreferences,
  Table,
} from '@cloudscape-design/components';
import CommonLayout from 'src/layout/CommonLayout';
import React, { useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import { IntentionExecutionItem, IntentionExecutionResponse } from 'src/types';
import { alertMsg, formatTime } from 'src/utils/utils';
// import useAxiosRequest from 'src/hooks/useAxiosRequest';
import { useTranslation } from 'react-i18next';

const IntentionDetail: React.FC = () => {
  
  const [loadingData, setLoadingData] = useState(false);
  const [executionFileList, setExecutionFileList] = useState<
    IntentionExecutionItem[]
  >([]);
  // const fetchData = useAxiosRequest();
  const { t } = useTranslation();
  const { id } = useParams();

  const getIntentionDetail = async () => {
    setLoadingData(true);
    try {
      // const data: IntentionExecutionResponse = await fetchData({
      //   url: `intention/executions/${id}`,
      //   method: 'get',
      // });
      // const executionRes: IntentionExecutionResponse = data;
      const executionRes: IntentionExecutionResponse = {
          Items:[{
               "s3Prefix": "intentions/Admin/Screenshot 2024-08-15 at 18.11.30.png",
               "s3Bucket": "intelli-agent-apiconstructllmbotintentionsfc4f8a7a-6vbr3vihybqs",
               "createTime": "2024-08-18 18:50:46.561202+00:00",
               "executionId": "2ed65d3d-3d78-4557-917f-a8fe4c65276f",
               "s3Path": "s3://intelli-agent-apiconstructllmbotintentionsfc4f8a7a-6vbr3vihybqs/intentions/Admin/Screenshot 2024-08-15 at 18.11.30.png",
               "status": "SUCCEED",
               "QAList": [
                {
                  question: "你来自哪里啊",
                  answer: "greeting",
                  kwargs: "This is the first item"
                },
                {
                  question: "怎么去天安门",
                  answer: "comfort",
                  kwargs: "This is the second item"
                },
                {
                  question: "今天天气如何",
                  answer: "comfort",
                  kwargs: "-"
                },
                {
                  question: "昨天是星期几",
                  answer: "comfort",
                  kwargs: "This is the fourth item"
                },
                {
                  question: "北京地铁几号线最拥挤",
                  answer: "get_weather",
                  kwargs:
                    "This is the fifth item with a longer description"
                },
                {
                  question: "国内前半年的GDP如何？",
                  answer: "general-rag",
                  kwargs: "This is the sixth item"
                }
              ]
          }],
          Count: 1
      }
      setExecutionFileList(executionRes.Items);
      setLoadingData(false);
    } catch (error: unknown) {
      setLoadingData(false);
      if (error instanceof Error) {
        alertMsg(error.message);
      }
    }
  };

  const getIntentionPrefix = (s3Path: string) => {
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
    console.log("into detail>>>>")
    getIntentionDetail();
  }, []);

  return (
    <CommonLayout
      isLoading={loadingData}
      activeHref="/intention"
      breadCrumbs={[
        {
          text: t('name'),
          href: '/',
        },
        {
          text: t('intention'),
          href: '/intention',
        },
        {
          text: `${id}`,
          href: '/detail',
        },
      ]}
    >
      <ContentLayout>
      <SpaceBetween direction="vertical" size="m">
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
              <b>{`${getIntentionPrefix(executionFileList?.[0]?.s3Path)}`} </b>
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
        <Container
          variant="default"
          header={
            <Header variant="h2" description={t('qaListDesc')}>
              {t('qaList')}
            </Header>
          }
        >
          <Table
      columnDefinitions={[
        {
          id: "question",
          header: "问题",
          cell: item => item.question,
          sortingField: "name",
          isRowHeader: true
        },
        {
          id: "answer",
          header: "意图",
          cell: item => item.answer,
          sortingField: "alt"
        },
        {
          id: "kwargs",
          header: "参数",
          cell: item => item.kwargs
        }
      ]}
      columnDisplay={[
        { id: "question", visible: true },
        { id: "answer", visible: true },
        { id: "kwargs", visible: true }
      ]}
      enableKeyboardNavigation
      items={executionFileList[0]?.QAList||[]}
      loadingText="Loading resources"
      stickyHeader
      trackBy="question"
      empty={
        <Box
          margin={{ vertical: "xs" }}
          textAlign="center"
          color="inherit"
        >
          <SpaceBetween size="m">
            <b>No resources</b>
            <Button>Create resource</Button>
          </SpaceBetween>
        </Box>
      }
      filter={
        <TextFilter
          filteringPlaceholder={t('findResources')}
          filteringText=""
        />
      }
      pagination={
        <Pagination currentPageIndex={1} pagesCount={2} />
      }
      preferences={
        <CollectionPreferences
          title="Preferences"
          confirmLabel="Confirm"
          cancelLabel="Cancel"
          preferences={{
            pageSize: 10,
            contentDisplay: [
              { id: "question", visible: true },
              { id: "answer", visible: true },
              { id: "kwargs", visible: true },
              { id: "comment", visible: true }
            ]
          }}
          pageSizePreference={{
            title: "Page size",
            options: [
              { value: 10, label: "10 resources" },
              { value: 20, label: "20 resources" }
            ]
          }}
          wrapLinesPreference={{}}
          stripedRowsPreference={{}}
          contentDensityPreference={{}}
          contentDisplayPreference={{
            options: [
              {
                id: "variable",
                label: "Variable name",
                alwaysVisible: true
              },
              { id: "value", label: "Text value" },
              { id: "type", label: "Type" },
              { id: "description", label: "Description" }
            ]
          }}
          stickyColumnsPreference={{
            firstColumns: {
              title: "Stick first column(s)",
              description:
                "Keep the first column(s) visible while horizontally scrolling the table content.",
              options: [
                { label: "None", value: 0 },
                { label: "First column", value: 1 },
                { label: "First two columns", value: 2 }
              ]
            },
            lastColumns: {
              title: "Stick last column",
              description:
                "Keep the last column visible while horizontally scrolling the table content.",
              options: [
                { label: "None", value: 0 },
                { label: "Last column", value: 1 }
              ]
            }
          }}
        />
      }
    />
        </Container>
        </SpaceBetween>
      </ContentLayout>
    </CommonLayout>
  );
};

export default IntentionDetail;
