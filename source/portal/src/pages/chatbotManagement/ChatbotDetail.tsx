import React, { useEffect, useState, useContext } from 'react';
// import KeyValuePairs from "@cloudscape-design/components/key-value-pairs";
import CommonLayout from 'src/layout/CommonLayout';
import {
  Alert,
  Box,
  Button,
  ButtonDropdown,
  // ButtonDropdown,
  CollectionPreferences,
  Container,
  ContentLayout,
  FormField,
  Grid,
  Header,
  Icon,
  Input,
  Pagination,
  SpaceBetween,
  Table,
  TextFilter,
} from '@cloudscape-design/components';
import {
  ChatbotItemDetail,
  ChatbotDetailResponse,
  IndexItem,
  IndexItemTmp
} from 'src/types';
import useAxiosRequest from 'src/hooks/useAxiosRequest';
import { useTranslation } from 'react-i18next';
import { alertMsg } from 'src/utils/utils';
import { useParams } from 'react-router-dom';

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
  const [indexList, setIndexList] = useState<IndexItem[]>([]);
  const [tmpIndexList, setTmpIndexList] = useState<IndexItemTmp[]>([]);
  const [tableIndexList, setTableIndexList] = useState<IndexItemTmp[]>([]);
  const [addIndexStatus, setAddIndexStatus] = useState(false)

  useEffect(()=>{
    getChatbotDetail();
  },[])
  
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
  const getChatbotIndex = async () =>{

  }

  const addNewIndex = () =>{
    setTmpIndexList([{
      name: "",
      type: "",
      description: "",
      tag: "",
      status: 'new'
    }, ...tmpIndexList])
    // tmpIndexList.unshift()
    setAddIndexStatus(true)
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
      setIndexList(chatbotDetail.index)
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
      label={t("createTime")}
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
                      getChatbotIndex();
                    }}
                  />
                  
                  
                  <Button variant="primary" onClick={addNewIndex}>
                  <Icon name="add-plus" /> {t('addIndex')}
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
      columnDefinitions={[
        {
          id: "name",
          header: t('indexName'),
          cell: item => {
            if(item.status === "old"){
              return item.name
            } else {
              return (<Input value={item.name}/>)
            }
          },
          sortingField: "name",
          isRowHeader: true,
        },
        {
          id: "type",
          header: t('indexType'),
          cell: item => {
            if(item.status === "old"){
              return item.type
            } else {
              return (<Input value={item.type}/>)
            }
          },
          sortingField: "type"
        },
        {
          id: "desc",
          header: t('desc'),
          cell: item => {
            if(item.status === "old"){
              return item.description
            } else {
              return (<Input value={item.description}/>)
            }
          },
          editConfig: {
            ariaLabel: "Name",
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
                  onChange={event =>
                    setValue(event.detail.value)
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
            if(item.status === "old"){
              return item.tag
            } else {
              return (<Input value={item.tag}/>)
            }
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
      loadingText="Loading resources"
      stickyHeader
      trackBy="name"
      sortingDisabled
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
               <Button>{t('button.discardChanges')}</Button>
               <Button variant="primary">{t('button.saveChanges')}</Button>
            </SpaceBetween>
          </div>
        </div>
        </SpaceBetween>
        
      </ContentLayout>
    </CommonLayout>
    );
};
export default ChatbotDetail;
