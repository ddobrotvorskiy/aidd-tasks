import { MailOutlined, PhoneOutlined, TeamOutlined } from '@ant-design/icons';
import { Avatar, Card, Space, Tag, Typography } from 'antd';
import React from 'react';
import { useNavigate } from 'react-router-dom';
import type { Employee } from '../types';

interface Props {
  employee: Employee;
}

const EmployeeCard: React.FC<Props> = ({ employee }) => {
  const navigate = useNavigate();

  return (
    <Card
      hoverable
      style={{ width: 280 }}
      onClick={() => navigate(`/employees/${employee.id}`)}
    >
      <Card.Meta
        avatar={
          <Avatar
            size={64}
            src={employee.photo_url ?? undefined}
            style={{ backgroundColor: '#1677ff' }}
          >
            {employee.full_name.charAt(0).toUpperCase()}
          </Avatar>
        }
        title={employee.full_name}
        description={
          <Space direction="vertical" size={2}>
            {employee.job_title && (
              <Typography.Text type="secondary">{employee.job_title}</Typography.Text>
            )}
            {employee.department && <Tag icon={<TeamOutlined />}>{employee.department}</Tag>}
            {employee.phone && (
              <Typography.Text>
                <PhoneOutlined /> {employee.phone}
              </Typography.Text>
            )}
            <Typography.Text>
              <MailOutlined /> {employee.email}
            </Typography.Text>
          </Space>
        }
      />
    </Card>
  );
};

export default EmployeeCard;
