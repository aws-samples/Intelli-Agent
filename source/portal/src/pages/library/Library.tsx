import React, { useContext, useEffect, useState } from 'react';
import CommonLayout from '../../layout/CommonLayout';
import {
  Box,
  BreadcrumbGroup,
  Button,
  Header,
  Link,
  SpaceBetween,
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
      <Table
        loading={loadingData}
        variant="full-page"
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
              <Link href="#">{item.executionId}</Link>
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
            id: 'status',
            header: 'Status',
            cell: (item: LibraryListItem) => item.executionStatus,
          },
        ]}
        enableKeyboardNavigation
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
          <TextFilter filteringPlaceholder="Find resources" filteringText="" />
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
                ? '(' + selectedItems.length + '/10)'
                : '(10)'
            }
          >
            Documents Library
          </Header>
        }
      />
    </CommonLayout>
  );
};

export default Library;
