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
import { IntentionExecutionItem, IntentionExecutionResponse, QAItem } from 'src/types';
import { alertMsg } from 'src/utils/utils';
import { useTranslation } from 'react-i18next';
import useAxiosRequest from 'src/hooks/useAxiosRequest';

const IntentionDetail: React.FC = () => {
  
  const pageSize = 10;
  const [currentPage, setCurrentPage] = useState(1);
  const [loadingData, setLoadingData] = useState(false);
  const [executionFileList, setExecutionFileList] = useState<
    IntentionExecutionItem[]
  >([]);
  const [tableQAList, setTableQAList] = useState<QAItem[]>(
    [],
  );
  const fetchData = useAxiosRequest();
  const { t } = useTranslation();
  const { id } = useParams();

  useEffect(() => {
    setTableQAList(
      executionFileList[0]?.QAList.slice(
        (currentPage - 1) * pageSize,
        currentPage * pageSize,
      ),
    );
  }, [currentPage, pageSize]);

  const getIntentionDetail = async () => {
    setLoadingData(true);
    try {
      const data: IntentionExecutionResponse = await fetchData({
        url: `intention/executions/${id}`,
        method: 'get',
      });
      const executionRes: IntentionExecutionResponse = data;
      // const executionRes: IntentionExecutionResponse = {
      //     Items:[{
      //          "s3Prefix": "intentions/Admin/基于周会讨论的QA对.xlsx",
      //          "s3Bucket": "intelli-agent-apiconstructllmbotdocumentsfc4f8a7a-6vbr3vihybqs",
      //          "createTime": "2022-08-21 17:28:32",
      //          "executionId": "2ed65d3d-3d78-4557-917f-a8fe4c65276f",
      //          "s3Path": "s3://intelli-agent-apiconstructllmbotdocumentsfc4f8a7a-6vbr3vihybqs/intentions/Admin/基于周会讨论的QA对.xlsx",
      //          "status": "SUCCEED",
      //          "QAList": [
      //             {"question": "Hi", "answer": "greeting", "kwargs": ""},
      //             {"question": "HI ADMIN", "answer": "greeting", "kwargs": ""},
      //             {"question": "你好", "answer": "greeting", "kwargs": ""},
      //             {"question": "My name is Jack", "answer": "greeting", "kwargs": ""},
      //             {"question": "good afternoon", "answer": "greeting", "kwargs": ""},
      //             {"question": "签署公会线下合作协议注意事项", "answer": "general-rag", "kwargs": ""},
      //             {"question": "公会承诺保底/底薪需注意哪些", "answer": "general-rag", "kwargs": ""},
      //             {"question": "从当前公会换到其他公会的操作流程", "answer": "general-rag", "kwargs": ""},
      //             {"question": "公会承诺可避税的可信度", "answer": "general-rag", "kwargs": ""},
      //             {"question": "公会承诺提供黑产服务的合规性", "answer": "general-rag", "kwargs": ""},
      //             {"question": "使用公会提供账号直播的风险", "answer": "general-rag", "kwargs": ""},
      //             {"question": "签署《主播及公会合作协议》的作用", "answer": "general-rag", "kwargs": ""},
      //             {"question": "主播退出当前公会的渠道", "answer": "general-rag", "kwargs": ""},
      //             {"question": "公会招募未成年主播的应对措施", "answer": "general-rag", "kwargs": ""},
      //             {"question": "公会教唆主播进行违规行为的处理方式", "answer": "general-rag", "kwargs": ""},
      //             {"question": "Ur game is not good", "answer": "comfort", "kwargs": ""},
      //             {"question": "Scaming to me", "answer": "comfort", "kwargs": ""},
      //             {"question": "your games is not fair, I never recommend your apps to anyone.", "answer": "comfort", "kwargs": ""},
      //             {"question": "All games im lost a lot of coins", "answer": "comfort", "kwargs": ""},
      //             {"question": "always lose. Waste of money", "answer": "comfort", "kwargs": ""},
      //             {"question": "What is the weather like in Shanghai today", "answer": "get_weather", "kwargs": "{\"city_name\": \"shanghai\"}"}
      //         ]
      //     }],
      //     Count: 1
      // }
      setExecutionFileList(executionRes.Items);
      setTableQAList(executionRes.Items[0]?.QAList.slice(0, pageSize));
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
                    {item.s3Prefix}
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
          id: "intention",
          header: "意图",
          cell: item => item.intention,
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
        { id: "intention", visible: true },
        { id: "kwargs", visible: true }
      ]}
      enableKeyboardNavigation
      items={tableQAList||[]}
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
            <b>{t('empty')}</b>
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
        <Pagination
              disabled={loadingData}
              currentPageIndex={currentPage}
              pagesCount={Math.ceil(executionFileList[0]?.QAList.length / pageSize)}
              onChange={({ detail }) => setCurrentPage(detail.currentPageIndex)}
            />
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
              { id: "intention", visible: true },
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
