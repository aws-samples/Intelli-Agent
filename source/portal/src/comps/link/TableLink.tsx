import { Link } from '@cloudscape-design/components';
import React from 'react';
import { useNavigate } from 'react-router-dom';

interface TableLinkProps {
  name: string;
  url: string;
}

const TableLink: React.FC<TableLinkProps> = (props: TableLinkProps) => {
  const { name, url } = props;
  const navigate = useNavigate();
  return (
    <Link
      onFollow={(e) => {
        e.preventDefault();
        navigate(url);
      }}
    >
      {name}
    </Link>
  );
};

export default TableLink;
