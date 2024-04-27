import React, { useContext, useEffect, useState } from 'react';
import CommonLayout from '../../layout/CommonLayout';
import {
  Box,
  BreadcrumbGroup,
  Button,
  ContentLayout,
  Header,
  Link,
  SpaceBetween,
  StatusIndicator,
  Table,
  TextFilter,
} from '@cloudscape-design/components';
import { useNavigate } from 'react-router-dom';
import ConfigContext from '../../context/config-context';
import { axios } from '../../utils/request';
import { LibraryListItem, LibraryListResponse } from 'types';

const Library: React.FC = () => {
  const [selectedItems, setSelectedItems] = useState<LibraryListItem[]>([]);
  const navigate = useNavigate();
  const config = useContext(ConfigContext);
  const [loadingData, setLoadingData] = useState(false);
  const [libraryList, setLibraryList] = useState<LibraryListItem[]>([]);

  const getLibraryList = async () => {
    setLoadingData(true);
    const params = {
      size: 9999,
      total: 9999,
    };
    const result = await axios.get(`${config?.apiUrl}/etl/list-execution`, {
      params,
    });
    const items: LibraryListResponse = result.data;
    setLibraryList(items.Items);
    setLoadingData(false);
  };

  useEffect(() => {
    getLibraryList();
  }, []);

  const renderStatus = (status: string) => {
    if (status === 'COMPLETED') {
      return <StatusIndicator type="success">Completed</StatusIndicator>;
    } else if (status === 'IN-PROGRESS') {
      return <StatusIndicator type="loading">In Progress</StatusIndicator>;
    } else {
      return <StatusIndicator type="error">Failed</StatusIndicator>;
    }
  };

  return (
    <CommonLayout
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
          ]}
        />
      }
    >
      <ContentLayout>
        <Table
          resizableColumns
          loading={loadingData}
          onSelectionChange={({ detail }) =>
            setSelectedItems(detail.selectedItems)
          }
          selectedItems={selectedItems}
          ariaLabels={{
            selectionGroupLabel: 'Items selection',
            allItemsSelectionLabel: ({ selectedItems }) =>
              `${selectedItems.length} ${
                selectedItems.length === 1 ? 'item' : 'items'
              } selected`,
          }}
          columnDefinitions={[
            {
              id: 'executionId',
              header: 'ID',
              cell: (item: LibraryListItem) => (
                <Link href={`/library/detail/${item.executionId}`}>
                  {item.executionId}
                </Link>
              ),
              sortingField: 'name',
              isRowHeader: true,
            },
            {
              id: 'bucket',
              header: 'Bucket',
              cell: (item: LibraryListItem) => item.s3Bucket,
              sortingField: 'alt',
            },
            {
              id: 'prefix',
              header: 'Prefix',
              cell: (item: LibraryListItem) => item.s3Prefix,
            },
            {
              width: 150,
              id: 'offline',
              header: 'Offline',
              cell: (item: LibraryListItem) => item.offline,
            },
            {
              width: 150,
              id: 'qaEnhance',
              header: 'QA Enhance',
              cell: (item: LibraryListItem) => item.qaEnhance,
            },
            {
              width: 150,
              id: 'indexType',
              header: 'Index Type',
              cell: (item: LibraryListItem) => item.indexType,
            },
            {
              width: 160,
              id: 'status',
              header: 'Status',
              cell: (item: LibraryListItem) =>
                renderStatus(item.executionStatus),
            },
          ]}
          items={libraryList}
          loadingText="Loading resources"
          selectionType="multi"
          trackBy="executionId"
          empty={
            <Box margin={{ vertical: 'xs' }} textAlign="center" color="inherit">
              <SpaceBetween size="m">
                <b>No resources</b>
                <Button>Create resource</Button>
              </SpaceBetween>
            </Box>
          }
          filter={
            <TextFilter
              filteringPlaceholder="Find resources"
              filteringText=""
            />
          }
          header={
            <Header
              actions={
                <SpaceBetween direction="horizontal" size="xs">
                  <Button
                    variant="primary"
                    onClick={() => {
                      navigate('/library/add');
                    }}
                  >
                    Create Docs Library
                  </Button>
                </SpaceBetween>
              }
              counter={
                selectedItems.length
                  ? `(${selectedItems.length}/${libraryList.length})`
                  : `(${libraryList.length})`
              }
            >
              Documents Library
            </Header>
          }
        />
      </ContentLayout>
    </CommonLayout>
  );
};

export default Library;
