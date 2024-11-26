import React, { useEffect, useState } from 'react';
// import KeyValuePairs from "@cloudscape-design/components/key-value-pairs";
import CommonLayout from 'src/layout/CommonLayout';
import {
  Box,
  Button,
  // ButtonDropdown,
  CollectionPreferences,
  Container,
  ContentLayout,
  FormField,
  Grid,
  Header,
  Icon,
  Input,
  Modal,
  Pagination,
  Select,
  SpaceBetween,
  Table,
  TextFilter,
} from '@cloudscape-design/components';
import {
  ChatbotItemDetail,
  ChatbotDetailResponse,
  IndexItemTmp,
  SelectedOption,
  CreEditChatbotResponse,
  ChatbotIndexResponse
} from 'src/types';
import useAxiosRequest from 'src/hooks/useAxiosRequest';
import { useTranslation } from 'react-i18next';
import { alertMsg } from 'src/utils/utils';
import { useNavigate, useParams } from 'react-router-dom';
import { INDEX_TYPE_OPTIONS } from 'src/utils/const';

const INITIAL_ADD_INDEX ={
  name:"",
  type:"qq",
  description:"",
  tag:"",
  status: "new"
}

const ChatbotDetail: React.FC = () => {
  const { t } = useTranslation();
  const { id } = useParams();
  const pageSize = 10;
  const fetchData = useAxiosRequest();
  const [chatbotDetail, setChatbotDetail] = useState<ChatbotItemDetail>(null as any)
  const [searchIndexName, setSearchIndexName] = useState("")
  const [currentPage, setCurrentPage] = useState(1);
  const [pageCount, setPageCount] = useState(1);
  const [loadingData, setLoadingData] = useState(false);
  // const [indexList, setIndexList] = useState<IndexItem[]>([]);
  const [tmpIndexList, setTmpIndexList] = useState<IndexItemTmp[]>([]);
  const [tableIndexList, setTableIndexList] = useState<IndexItemTmp[]>([]);
  const [addedIndex, setAddedIndex] = useState<IndexItemTmp>(INITIAL_ADD_INDEX)
  const [errText, setErrText] = useState("")
  const [selectedIndexTypeOption, setSelectedIndexTypeOption] = useState<SelectedOption>({label:"qq", value:"qq"})
  const [addIndexModel, setAddIndexModel] = useState(false)
  const [tmpDesc, setTmpDesc] = useState('')
  const navigate = useNavigate();
  const [loadingSave, setLoadingSave] = useState(false)

  useEffect(()=>{
    getChatbotDetail();
  },[])

  useEffect(()=>{
    setSelectedIndexTypeOption({
      label: addedIndex.type,
      value: addedIndex.type
    })

  },[addedIndex.type])

  useEffect(()=>{
    setErrText("")
    setAddedIndex(INITIAL_ADD_INDEX)
  },[addIndexModel])
  
  useEffect(() => {
    let list = tmpIndexList
    if(searchIndexName!=null && searchIndexName.length > 0){
        list = list?.filter(item => item.name.indexOf(searchIndexName)>-1);
    }
    setPageCount(Math.ceil(list?.length / pageSize))
    setTableIndexList(
      list?.slice(
        (currentPage - 1) * pageSize,
        currentPage * pageSize,
      ),
    );
  }, [currentPage, pageSize, searchIndexName, tmpIndexList.length]);
  
  
  const getChatbotIndexes = async () =>{
    setLoadingData(true);
    const params = {
      max_items: 9999,
      page_size: 9999,
    };
    try {
      const data = await fetchData({
        url: `chatbot-management/indexes/${chatbotDetail.chatbotId}`,
        method: 'get',
        params,
      });
      const items: ChatbotIndexResponse = data;
      const preSortItem = items.Items.map((index) => {
        return {
          ...index,
          status: "old",
        };
      });
      // setAllChatbotList(preSortItem);
      setChatbotDetail((prev)=>{
           return {
            ...prev,
            index: preSortItem
           }
      })
      setTableIndexList(preSortItem.slice(0, pageSize));
      setLoadingData(false);
    } catch (error: unknown) {
      setLoadingData(false);
    }
  }

  const discardChange = ()=>{
    navigate("/chatbot-management")
  }
  const addNewIndex = () =>{
    setAddIndexModel(true)
  }

  const saveAddedIndex = async ()=>{
    if(addedIndex.name?.trim().length === 0){
      setErrText(t('validation.indexNameEmpty'))
      return
    }

    const bot_index_list = tmpIndexList.map(item=> item.name)

    if(bot_index_list.includes(addedIndex.name)){
      setErrText(t('validation.repeatedIndex'))
      return
    }
    const indexCheck = await isValidIndex()
    if(!indexCheck.result){
      setErrText(indexCheck.reason==1?t('validation.repeatIndex'):t('validation.indexValid'))
      return
    }
    setTmpIndexList([addedIndex, ...tmpIndexList])
    setAddIndexModel(false)
  }

  const updateChatbot = async ()=>{
    setLoadingSave(true);
    const indexList = tmpIndexList.map(({status,...rest})=> rest)
    // const index = {}
    
    try {
      const createRes: CreEditChatbotResponse = await fetchData({
        url: 'chatbot-management/edit-chatbot',
        method: 'post',
        data: {
          chatbotId: chatbotDetail.chatbotId,
          modelId: chatbotDetail.model,
          modelName: chatbotDetail.model,
          index: genBotIndexCreate(indexList),
        },
      });
      // const createRes: CreateChatbotResponse = data;
      if (createRes.Message === 'OK') {
        setLoadingSave(false);
        alertMsg(t('updated'), 'success');
        setTimeout(() => {
          setLoadingSave(false);
          navigate("/chatbot-management")
        }, 1500);
        
        // setShowCreate(false);
        // setShowEdit(false);
        // getChatbotList();
      }
      // setLoadingSave(false);
    } catch (error: unknown) {
      setLoadingSave(false);
    }
  }

  const genBotIndexCreate = (indexList: any[])=>{
    let index:any={}
    indexList.map((item: any)=>{
      if (!index[item.type]) {
        index[item.type] = {};
      }
      index[item.type][item.name] = item.description||'';
    });
    return index
  }

  const isValidIndex = async () =>{
    return await fetchData({
      url: `chatbot-management/check-index`,
      method: 'post',
      data: {
        index: addedIndex.name,
        model: chatbotDetail.model
      },
    });
    // return 
  }
  const getChatbotDetail = async () => {
    setLoadingData(true);
    try {
      const data: ChatbotDetailResponse = await fetchData({
        url: `chatbot-management/chatbots/${id}`,
        method: 'get',
      });
      const chatbotDetail: ChatbotItemDetail = {
        chatbotId: data.chatbotId,
        model: data.model?.model_name,
        index: data.index,
        updateTime: data.updateTime
      };
      setChatbotDetail(chatbotDetail)
      // setIndexList(chatbotDetail.index)
      const tmpIndexList = chatbotDetail.index.map(item => ({
        ...item,
        status: 'old'
      }))
      setTmpIndexList(tmpIndexList)
      setTableIndexList(tmpIndexList?.slice(0, pageSize));
      setLoadingData(false);
    } catch (error: unknown) {
      setLoadingData(false);
      if (error instanceof Error) {
        alertMsg(error.message);
      }
    }
  }


  

  return (
    <CommonLayout
      activeHref="/chatbots"
      breadCrumbs={[
        {
          text: t('name'),
          href: '/',
        },
        {
          text: t('chatbot'),
          href: '/chatbots',
        },
      ]}
    >
      <ContentLayout>
        <SpaceBetween direction="vertical" size="m">
        <Container
          variant="default"
          
          header={
            <Header
              variant="h2"
            
              >
              {t('chatbotDetail')}
            </Header>
          }
        >
          <SpaceBetween direction="vertical" size="xs">
            
            <div className="mt-10">
            <Grid
      gridDefinition={[{ colspan: 4 }, { colspan: 4 }, { colspan: 4 }]}
    >
      <div>
      <FormField
      description={id}
      
      label={t("chatbotName")}
    >
    </FormField>
      </div>
      <div>
      <FormField
      description={chatbotDetail?.model}
      label={t("embeddingModel")}
    >
    </FormField>
      </div>
      <div>
      <FormField
      description={chatbotDetail?.updateTime}
      label={t("updateTime")}
    >
    </FormField>
      </div>
    </Grid>
            </div>
            
          </SpaceBetween>
        </Container>
        <Container
          variant="default"
          header={
            <Header variant="h2"
              description={t('indexListDesc')}
              actions={
                <SpaceBetween
                  direction="horizontal"
                  size="xs"
                >
                  <Button
                    iconName="refresh"
                    loading={loadingData}
                    onClick={() => {
                      getChatbotIndexes();
                    }}
                  />
                  
                  
                  <Button variant="primary" onClick={addNewIndex}>
                  <Icon name="add-plus" /> {t('addNewIndex')}
                  </Button>
                </SpaceBetween>
              }
              >
              {t('indexList')}
            </Header>
          }
        >
          <Table
          loading={loadingData}
          ariaLabels={{
            activateEditLabel: (column, item) =>
              `Edit ${item.name} ${column.header}`,
            cancelEditLabel: column =>
              `Cancel editing ${column.header}`,
            submitEditLabel: column =>
              `Submit editing ${column.header}`,
            tableLabel: "Table with inline editing"
          }}
      columnDefinitions={[
        {
          id: "name",
          header: t('indexName'),
          cell: item => {
            return item.name
          },
          sortingField: "name",
          isRowHeader: true,
        },
        {
          id: "type",
          header: t('indexType'),
          cell: item => {
              return item.type
          },
          sortingField: "type"
        },
        {
          id: "desc",
          header: t('desc'),
          cell: item => {
              return item.description
          },
          editConfig: {
            ariaLabel: "Description",
            editIconAriaLabel: "editable",
            errorIconAriaLabel: "Name Error",
            editingCell: (
              item,
              { currentValue, setValue }
            ) => {
              return (
                <Input
                  autoFocus={true}
                  value={currentValue ?? item.description}
                  onChange={event => {
                    setValue(event.detail.value)
                    setTmpDesc(currentValue)
                    }
                  }
                />
              );
            },
          }
        },
        {
          id: "tag",
          header: t('tag'),
          cell: item => {
              return item.tag
          },
        }
      ]}
      columnDisplay={[
        { id: "name", visible: true },
        { id: "type", visible: true },
        { id: "desc", visible: true },
        { id: "tag", visible: true }
      ]}
      enableKeyboardNavigation
      items={tableIndexList||[]}
      submitEdit={async (item: IndexItemTmp) => {
        item.description = tmpDesc
      }}
      loadingText="Loading resources"
      stickyHeader
      trackBy="name"
      sortingDisabled
      empty={
        <Box margin={{ vertical: 'xs' }} textAlign="center" color="inherit">
          <SpaceBetween size="m">
            <b>{t('noData')}</b>
          </SpaceBetween>
        </Box>
      }
      filter={
        <TextFilter
          filteringPlaceholder={t('findResources')}
          filteringText={searchIndexName}
          onChange={({ detail }) => setSearchIndexName(detail.filteringText)}
        />
      }
      pagination={
        <Pagination
              disabled={loadingData}
              currentPageIndex={currentPage}
              pagesCount={pageCount}
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
              { id: "name", visible: true },
              { id: "type", visible: true },
              { id: "desc", visible: true },
              { id: "tag", visible: true }
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
        <div style={{display: "flex"}}>
          {/* <div></div>í */}
          <div style={{marginLeft:'auto'}}>
            <SpaceBetween size={'s'} direction='horizontal'>
               <Button onClick={()=>discardChange()}>{t('button.discardChanges')}</Button>
               <Button variant="primary" onClick={()=>updateChatbot()} loading={loadingSave}>{t('button.saveChanges')}</Button>
            </SpaceBetween>
          </div>
        </div>
        </SpaceBetween>
        <Modal
      onDismiss={() => setAddIndexModel(false)}
      visible={addIndexModel}
      footer={
        <Box float="right">
          <SpaceBetween direction="horizontal" size="xs">
            <Button variant="link" onClick={()=>setAddIndexModel(false)}>{t('button.cancel')}</Button>
            <Button variant="primary" onClick={()=>saveAddedIndex()}>{t('button.save')}</Button>
          </SpaceBetween>
        </Box>
      }
      header={<Header
      variant="h2"
      description={<>{t('addIndexDesc')}{chatbotDetail?.chatbotId}</>}
      >
      {t('addIndex')}
    </Header>}
      
      
    >
      <SpaceBetween size={'m'} direction='vertical'>
      <div style={{height:5}}></div>
      <FormField
        label={t('indexName')}
        description={t('indexNameDesc')}
        errorText={errText}
      >
        <Input 
          value={addedIndex.name} 
          placeholder={t('indexPlaceholder')}
          onChange={({ detail }) => {
            setAddedIndex({...addedIndex, name: detail.value, tag: detail.value})
          }}
          />
      </FormField>
      <FormField
        label={t('indexType')}
        description={t('indexTypeDesc')}
      >
        <Select 
        selectedOption={selectedIndexTypeOption} 
        options={INDEX_TYPE_OPTIONS}
        onChange={({ detail }:{detail: any})=>setAddedIndex({...addedIndex, type: detail.selectedOption.value})}
        />
      </FormField>
      <FormField
        label={<>{t('desc')} - {t('optional')}</>}
        description={t('indexDescription')}
      >
        <Input 
          value={addedIndex.description} 
          placeholder={t('indexPlaceholderDesc')}
          onChange={({ detail }) => {
            setAddedIndex({...addedIndex, description: detail.value})
          }}
          />
      </FormField>
      <div style={{height:15}}></div>
      </SpaceBetween>
    </Modal>
      </ContentLayout>
    </CommonLayout>
    );
};
export default ChatbotDetail;
