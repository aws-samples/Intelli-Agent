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
  TableProps,
} from '@cloudscape-design/components';
import './style.scss';
import CommonLayout from 'src/layout/CommonLayout';
import React, { useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import { IntentionExecutionItem, IntentionExecutionResponse, QAItem } from 'src/types';
import { alertMsg } from 'src/utils/utils';
import { useTranslation } from 'react-i18next';
import useAxiosRequest from 'src/hooks/useAxiosRequest';
import { ROUTES } from 'src/utils/const';

const IntentionDetail: React.FC = () => {
  
  const pageSize = 10;
  const [currentPage, setCurrentPage] = useState(1);
  const [searchQuestionName, setSearchQuestionName] = useState("")
  const [pageCount, setPageCount] = useState(1)
  const [loadingData, setLoadingData] = useState(false);
  const [executionFileList, setExecutionFileList] = useState<
    IntentionExecutionItem[]
  >([]);
  const [qaList, setQaList] = useState<QAItem[]>(
    [],
  );
  const [tableQAList, setTableQAList] = useState<QAItem[]>(
    [],
  );
  const fetchData = useAxiosRequest();
  const { t } = useTranslation();
  const { id } = useParams();
  const [sortingColumn, setSortingColumn] = useState<
    TableProps.SortingColumn<QAItem>
  >({
    sortingField: 'status',
  });
  const [isDescending, setIsDescending] = useState<boolean | undefined>(true);

  useEffect(() => {
    let list = qaList
    if(searchQuestionName!=null && searchQuestionName.length > 0){
        list = list?.filter(item => item.question.indexOf(searchQuestionName)>-1);
    }
    setPageCount(Math.ceil(list?.length / pageSize))
    setTableQAList(
      list?.slice(
        (currentPage - 1) * pageSize,
        currentPage * pageSize,
      ),
    );
  }, [currentPage, pageSize, searchQuestionName]);

  const getIntentionDetail = async () => {
    setLoadingData(true);
    try {
      const data: IntentionExecutionResponse = await fetchData({
        url: `intention/executions/${id}`,
        method: 'get',
      });
      const executionRes: IntentionExecutionResponse = data;
      setExecutionFileList(executionRes.items);
      setQaList(executionRes.items[0]?.qaList);
      setPageCount(Math.ceil(executionRes.items[0]?.qaList?.length / pageSize))
      setTableQAList(executionRes.items[0]?.qaList.slice(0, pageSize));
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
      activeHref={ROUTES.Intention}
      breadCrumbs={[
        {
          text: t('name'),
          href: ROUTES.Home,
        },
        {
          text: t('intention'),
          href: ROUTES.Intention,
        },
        {
          text: `${id}`,
          href: '/detail',
        },
      ]}
    >
      <ContentLayout>
      <div style={{marginTop: '25px'}} />
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
            {executionFileList?.length > 0 ? (
              executionFileList.map((item) => (
                <div className="flex align-center" key={item.s3Prefix}>
                  <StatusIndicator type={showIngestStatus(item.status)}>
                    {item.s3Prefix}&nbsp;&nbsp;({t('successed')}:  {item.detail?.split("/")[0]}/{t('total')}: {item.detail?.split("/")[1]})
                  </StatusIndicator>
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
          variant="embedded"
      columnDefinitions={[
        {
          id: "question",
          header: t('question'),
          cell: item => item.question,
          // sortingField: "name",
          isRowHeader: true
        },
        {
          id: "intention",
          header: t('intention'),
          cell: item => item.intention,
          // sortingField: "alt"
        },
        {
          id: "kwargs",
          header: t('args'),
          cell: item => {
             if(item.kwargs){

              return  item.kwargs
             } else {
              return "-"
             }
          }
        },
        {
          id: "status",
          header: t('status'),
          sortingField: "status",
          cell: item => {
            if(!item.is_valid){
            return <Popover
            dismissButton={false}
            position="top"
            size="small"
            triggerType="custom"
            content={
              <span style={{color: "red"}}>
                {t("intentionFailMsg")}
              </span>
            }
          ><StatusIndicator type="error">{t("intentionFail")}</StatusIndicator></Popover>
          } 
          // else if(executionFileList[0]?.status === "FAILED"){
          //   return <Popover
          //   dismissButton={false}
          //   position="top"
          //   size="small"
          //   triggerType="custom"
          //   content={
          //     <span style={{color: "red"}}>
          //       {executionFileList[0]?.detail}
          //     </span>
          //   }><StatusIndicator type="error">{t("intentionFail")}</StatusIndicator></Popover>
          // } 
          else {
            return <StatusIndicator>{t("intentionSuccess")}</StatusIndicator>
          }
          }
        }
      ]}
      columnDisplay={[
        { id: "question", visible: true },
        { id: "intention", visible: true },
        { id: "kwargs", visible: true },
        { id: "status", visible: true }
      ]}
      sortingColumn={sortingColumn}
      sortingDescending={isDescending}
      onSortingChange={({detail}) => {
        const { sortingColumn, isDescending } = detail;
        console.log(sortingColumn.sortingField, isDescending)
        const sortedItems = [...executionFileList[0]?.qaList].sort((a, b) => {
          setSortingColumn(sortingColumn);
          setIsDescending(isDescending);
          if (sortingColumn.sortingField === 'status') {
            return !isDescending
              ? String(a.is_valid).localeCompare(String(b.is_valid))
              : String(b.is_valid).localeCompare(String(a.is_valid));
          }
          return 0;
        });
        setQaList(sortedItems);
        setTableQAList(sortedItems?.slice(
          (currentPage - 1) * pageSize,
          currentPage * pageSize,
        ),);
      }}
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
          filteringText={searchQuestionName}
          onChange={({ detail }) => setSearchQuestionName(detail.filteringText)}
        />
      }
      pagination={
        <Pagination
              disabled={loadingData}
              currentPageIndex={currentPage}
              pagesCount={
                pageCount
              }
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
