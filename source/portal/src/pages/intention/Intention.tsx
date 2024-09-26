import React, { useCallback, useEffect, useRef, useState } from 'react';
import CommonLayout from 'src/layout/CommonLayout';
import {
  Box,
  Button,
  CollectionPreferences,
  ContentLayout,
  Header,
  Modal,
  Pagination,
  SpaceBetween,
  StatusIndicator,
  Table,
  TableProps,
} from '@cloudscape-design/components';
import { IntentionsItem, IntentionsResponse, SelectedOption } from 'src/types';
import { formatTime } from 'src/utils/utils';
import TableLink from 'src/comps/link/TableLink';
import useAxiosRequest from 'src/hooks/useAxiosRequest';
import { useTranslation } from 'react-i18next';
import AddIntention from '../components/AddIntention';
// import { useAuth } from 'react-oidc-context';
import { EMBEDDING_MODEL_LIST } from 'src/utils/const';

const parseDate = (item: IntentionsItem) => {
  return item.createTime ? new Date(item.createTime) : 0;
};

const Intention: React.FC = () => {
  const [selectedItems, setSelectedItems] = useState<IntentionsItem[]>([]);
  const fetchData = useAxiosRequest();
  const [visible, setVisible] = useState(false);
  const { t } = useTranslation();
  const [loadingData, setLoadingData] = useState(false);
  const [allIntentions, setAllIntentions] = useState<IntentionsItem[]>([]);
  const [tableIntentions, setTableIntentions] = useState<IntentionsItem[]>(
    [],
  );
  const [currentPage, setCurrentPage] = useState(1);
  const [pageSize, setPageSize] = useState(10);
  const [indexName, setIndexName] = useState('');
  // const [loadingDelete, setLoadingDelete] = useState(false);
  const [sortingColumn, setSortingColumn] = useState<
    TableProps.SortingColumn<IntentionsItem>
  >({
    sortingField: 'createTime',
  });
  const [isDescending, setIsDescending] = useState<boolean | undefined>(true);
  // const auth = useAuth();
  // ingest document
  const [showAddModal, setShowAddModal] = useState(false);
  const isFirstRender = useRef(true);
  const [botsOption, setBotsOption] = useState<SelectedOption[]>([]);
  const [selectedBotsOption, setSelectedBotsOption] = useState<SelectedOption>();
  const [models, setModels] = useState<SelectedOption[]>([])
  const [selectedModelOption, setSelectedModelOption] = useState<SelectedOption>();
  const [useDefaultIndex, setUseDefaultIndex] = useState(true);
  const [fileEmptyError, setFileEmptyError] = useState(false);
  const [indexNameError, setIndexNameError] = useState('');
  const [uploadFiles, setUploadFiles] = useState<File[]>([]);

  const changeBotOption = (selectedBotOption: SelectedOption)=>{
    setSelectedBotsOption(selectedBotOption)
    if(useDefaultIndex){
      setIndexName(`${selectedBotOption.value.toLocaleLowerCase()}-intention-default`)
    }
  }

  // const changeUseDefaultIndex = (useDefault: boolean)=>{
  //    console.log(!useDefault)
  //    setUseDefaultIndex(!useDefault)
  // }

  const changeModelOption = (selectedBotOption: SelectedOption)=>{
    setSelectedModelOption(selectedBotOption)
  }

  const getIntentionList = async () => {
    setLoadingData(true);
    setSelectedItems([]);
    const params = {
      max_items: 9999,
      page_size: 9999,
    };
    try {
      const res: IntentionsResponse = await fetchData({
        url: 'intention/executions',
        method: 'get',
        params,
      });
      const preSortItem = res.Items

      preSortItem.sort((a, b) => {
        return Number(parseDate(b)) - Number(parseDate(a));
      });
      setAllIntentions(preSortItem);
      const tabdata = preSortItem.slice(0, pageSize)
      // const tabdata = preSortItem
      setTableIntentions(tabdata);
      setLoadingData(false);
    } catch (error: unknown) {
      setLoadingData(false);
    }
  };

  const getBots = async ()=>{
    // const groupName: string[] = auth?.user?.profile?.['cognito:groups'] as any;
    const data: any = await fetchData({
      url: 'chatbot-management/chatbots',
      method: 'get',
      // data: {
      //   groupName: groupName?.[0] ?? 'Admin',
      // },
    });
    const options: SelectedOption[] = [];
    (data.chatbot_ids||[]).forEach((item:any)=>{
      options.push({
         label: item,
         value: item
      })
    })

    // options.push({
    //   label: "Test",
    //   value: "Test"
    // })
    setBotsOption(options)
    setSelectedBotsOption(options[0])
    setIndexName(`${options[0].value.toLocaleLowerCase()}-intention-default`)
  }

  useEffect(()=>{
    if(useDefaultIndex == false){
      setIndexName("")
    } else {
      setIndexName(`${selectedBotsOption?.value.toLocaleLowerCase()}-intention-default`)
    }

  },[useDefaultIndex])

  // const getExistedIndex = async ()=>{
  //   const data: any = await fetchData({
  //     url: 'intention/get-all-index',
  //     method: 'get',
  //     data: {
  //       groupName: groupName?.[0] ?? 'Admin',
  //     },
  //   });

  // }

  const getModels  = async ()=>{
    const tempModels:{label: string; value:string}[] =[]

    EMBEDDING_MODEL_LIST.forEach((item: {model_id: string; model_name: string})=>{
       tempModels.push({
            label: item.model_name,
            value: item.model_id
       })
    })
    setModels(tempModels)
    setSelectedModelOption(tempModels[0])
  }

  useEffect(() => {
    getIntentionList();
    getBots();
    getModels();
    // getExistedIndex();
  }, []);

  useEffect(() => {
    if (isFirstRender.current) {
      isFirstRender.current = false;
      return;
    }
    setTableIntentions(
      allIntentions.slice(
        (currentPage - 1) * pageSize,
        currentPage * pageSize,
      ),
    );
  }, [currentPage, pageSize, allIntentions]);

  const renderStatus = (status: string) => {
    if (status === 'COMPLETED') {
      return <StatusIndicator type="success">{t('completed')}</StatusIndicator>;
    } else if (status === 'IN-PROGRESS') {
      return (
        <StatusIndicator type="loading">{t('inProgress')}</StatusIndicator>
      );
    } else {
      return <StatusIndicator type="error">{t('failed')}</StatusIndicator>;
    }
  };

  const LinkComp = useCallback(
    (item: IntentionsItem) => (
      <TableLink
        url={`/intention/detail/${item.executionId}`}
        name={item.executionId}
      />
    ),
    [],
  );

  return (
    <CommonLayout
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
      ]}
    >
      <ContentLayout>
        <Table
          resizableColumns
          loading={loadingData}
          onSelectionChange={({ detail }) =>
            setSelectedItems(detail.selectedItems)
          }
          sortingDescending={isDescending}
          sortingColumn={sortingColumn}
          onSortingChange={({ detail }) => {
            const { sortingColumn, isDescending } = detail;
            const sortedItems = [...tableIntentions].sort((a, b) => {
              setSortingColumn(sortingColumn);
              setIsDescending(isDescending);
              if (sortingColumn.sortingField === 'createTime') {
                return !isDescending
                  ? Number(parseDate(a)) - Number(parseDate(b))
                  : Number(parseDate(b)) - Number(parseDate(a));
              }
              if (sortingColumn.sortingField === 'fileName') {
                return !isDescending
                  ? a.fileName.localeCompare(b.fileName)
                  : b.fileName.localeCompare(a.fileName);
              }
              if (sortingColumn.sortingField === 'executionStatus') {
                return !isDescending
                  ? a.executionStatus.localeCompare(b.executionStatus)
                  : b.executionStatus.localeCompare(a.executionStatus);
              }
              return 0;
            });
            setTableIntentions(sortedItems);
          }}
          selectedItems={selectedItems}
          ariaLabels={{
            allItemsSelectionLabel: ({ selectedItems }) =>
              `${selectedItems.length} ${
                selectedItems.length === 1 ? t('item') : t('items')
              } ${t('selected')}`,
          }}
          columnDefinitions={[
            {
              id: 'executionId',
              header: t('id'),
              cell: (item: IntentionsItem) => LinkComp(item),
              isRowHeader: true,
            },
            {
              id: 'fileName',
              header: t('intentionName'),
              sortingField: 'fileName',
              cell: (item: IntentionsItem) => {
                const index = item.fileName.indexOf(']');
                if (index !== -1) {
                  return item.fileName.substring(index + 1).trim();
                } else {
                  return item.fileName;
                }
              },
            },
            {
              width: 150,
              id: 'chatbotId',
              header: t('chatbotName'),
              sortingField: 'chatbotId',
              cell: (item: IntentionsItem) =>
                item.chatbotId,
            },
            {
              width: 150,
              id: 'index',
              header: t('indexName'),
              sortingField: 'index',
              cell: (item: IntentionsItem) =>
                item.index,
            },
            {
              width: 150,
              id: 'model',
              header: t('modelName'),
              sortingField: 'model',
              cell: (item: IntentionsItem) =>
                item.model,
            },{
              width: 150,
              id: 'tag',
              header: t('tag'),
              sortingField: 'tag',
              cell: (item: IntentionsItem) =>
                item.tag,
            }
            ,{
              width: 150,
              id: 'executionStatus',
              header: t('status'),
              sortingField: 'executionStatus',
              cell: (item: IntentionsItem) =>
                renderStatus(item.executionStatus),
            },
            {
              width: 180,
              id: 'createTime',
              header: t('createTime'),
              sortingField: 'createTime',
              cell: (item: IntentionsItem) => formatTime(item.createTime),
            },
          ]}
          items={tableIntentions||[]}
          loadingText={t('loadingData')}
          trackBy="executionId"
          empty={
            <Box margin={{ vertical: 'xs' }} textAlign="center" color="inherit">
              <SpaceBetween size="m">
                <b>{t('noData')}</b>
              </SpaceBetween>
            </Box>
          }
          pagination={
            <Pagination
              disabled={loadingData}
              currentPageIndex={currentPage}
              pagesCount={Math.ceil(allIntentions.length / pageSize)}
              onChange={({ detail }) => setCurrentPage(detail.currentPageIndex)}
            />
          }
          preferences={
            <CollectionPreferences
              title={t('preferences')}
              confirmLabel={t('button.confirm')}
              cancelLabel={t('button.cancel')}
              onConfirm={({ detail }) => {
                setPageSize(detail.pageSize ?? 10);
                setCurrentPage(1);
              }}
              preferences={{
                pageSize: pageSize,
              }}
              pageSizePreference={{
                title: t('pageSize'),
                options: [10, 20, 50, 100].map((size) => ({
                  value: size,
                  label: `${size} ${t('items')}`,
                })),
              }}
            />
          }
          header={
            <Header
              actions={
                <SpaceBetween direction="horizontal" size="xs">
                  <Button
                    iconName="refresh"
                    loading={loadingData}
                    onClick={() => {
                      getIntentionList();
                    }}
                  />
                  {/* <Button
                    disabled={selectedItems.length <= 0}
                    onClick={() => {
                      setVisible(true);
                    }}
                  >
                    {t('button.delete')}
                  </Button> */}
                  <Button
                    variant="primary"
                    onClick={() => {
                      setUseDefaultIndex(true)
                      setFileEmptyError(false)
                      setIndexNameError('')
                      setShowAddModal(true)
                      setUploadFiles([])
                    }}
                  >
                    {t('button.createIntention')}
                  </Button>
                </SpaceBetween>
              }
              counter={
                selectedItems.length
                  ? `(${selectedItems.length}/${allIntentions.length})`
                  : `(${allIntentions.length})`
              }
            >
              {t('intention')}
            </Header>
          }
        />
        <Modal
          onDismiss={() => setVisible(false)}
          visible={visible}
          footer={
            <Box float="right">
              <SpaceBetween direction="horizontal" size="xs">
                <Button
                  variant="link"
                  onClick={() => {
                    setVisible(false);
                  }}
                >
                  {t('button.cancel')}
                </Button>
              </SpaceBetween>
            </Box>
          }
          header={t('alert')}
        >
          <Box variant="h4">{t('deleteTips')}</Box>
          <div className="selected-items-list">
            <ul className="gap-5 flex-v">
              {selectedItems.map((item) => (
                <li key={item.executionId}>{item.fileName}</li>
              ))}
            </ul>
          </div>
        </Modal>
        <AddIntention
          models={models}
          indexName={indexName}
          useDefaultIndex={useDefaultIndex}
          botsOption={botsOption}
          showAddModal={showAddModal}
          selectedModelOption={selectedModelOption}
          selectedBotOption={selectedBotsOption}
          uploadFiles={uploadFiles}
          setIndexName={setIndexName}
          changeUseDefaultIndex={setUseDefaultIndex}
          changeBotOption={changeBotOption}
          changeSelectedModel={changeModelOption}
          setShowAddModal={setShowAddModal}
          fileEmptyError={fileEmptyError} 
          indexNameError={indexNameError} 
          setFileEmptyError={setFileEmptyError} 
          setIndexNameError={setIndexNameError}
          setUploadFiles={setUploadFiles}
          reloadIntention={() => {
            setTimeout(() => {
              getIntentionList();
            }, 2000);
          } }
        />
        
      </ContentLayout>
    </CommonLayout>
  );
};

export default Intention;