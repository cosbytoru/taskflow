"""Implement organizations, roles, and tickets

Revision ID: cc0d14048736
Revises: edfba8c7e4a7
Create Date: 2025-06-15 03:07:51.712289

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'cc0d14048736'
down_revision = 'edfba8c7e4a7'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('organizations',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('name', sa.String(length=120), nullable=False),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('name')
    )
    op.create_table('roles',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('name', sa.String(length=80), nullable=False),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('name')
    )
    op.create_table('tickets',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('title', sa.String(length=255), nullable=False),
    sa.Column('status', sa.String(length=50), nullable=False),
    sa.Column('due_date', sa.Date(), nullable=True),
    sa.Column('priority', sa.Integer(), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=True),
    sa.Column('organization_id', sa.Integer(), nullable=False),
    sa.Column('requester_id', sa.Integer(), nullable=False),
    sa.Column('assignee_id', sa.Integer(), nullable=True),
    sa.ForeignKeyConstraint(['assignee_id'], ['users.id'], ),
    sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], ),
    sa.ForeignKeyConstraint(['requester_id'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('subtickets',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('title', sa.String(length=255), nullable=False),
    sa.Column('completed', sa.Boolean(), nullable=False),
    sa.Column('ticket_id', sa.Integer(), nullable=False),
    sa.ForeignKeyConstraint(['ticket_id'], ['tickets.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.drop_table('subtasks')
    op.drop_table('tasks')
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.add_column(sa.Column('organization_id', sa.Integer(), nullable=False))
        batch_op.add_column(sa.Column('role_id', sa.Integer(), nullable=False))
        batch_op.drop_constraint(batch_op.f('users_username_key'), type_='unique')
        batch_op.create_unique_constraint('_username_org_uc', ['username', 'organization_id'])
        batch_op.create_foreign_key(None, 'organizations', ['organization_id'], ['id'])
        batch_op.create_foreign_key(None, 'roles', ['role_id'], ['id'])

    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.drop_constraint(None, type_='foreignkey')
        batch_op.drop_constraint(None, type_='foreignkey')
        batch_op.drop_constraint('_username_org_uc', type_='unique')
        batch_op.create_unique_constraint(batch_op.f('users_username_key'), ['username'], postgresql_nulls_not_distinct=False)
        batch_op.drop_column('role_id')
        batch_op.drop_column('organization_id')

    op.create_table('tasks',
    sa.Column('id', sa.INTEGER(), server_default=sa.text("nextval('tasks_id_seq'::regclass)"), autoincrement=True, nullable=False),
    sa.Column('title', sa.VARCHAR(length=255), autoincrement=False, nullable=False),
    sa.Column('completed', sa.BOOLEAN(), autoincrement=False, nullable=False),
    sa.Column('user_id', sa.INTEGER(), autoincrement=False, nullable=False),
    sa.Column('due_date', sa.DATE(), autoincrement=False, nullable=True),
    sa.Column('priority', sa.INTEGER(), autoincrement=False, nullable=True),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], name='tasks_user_id_fkey'),
    sa.PrimaryKeyConstraint('id', name='tasks_pkey'),
    postgresql_ignore_search_path=False
    )
    op.create_table('subtasks',
    sa.Column('id', sa.INTEGER(), autoincrement=True, nullable=False),
    sa.Column('title', sa.VARCHAR(length=255), autoincrement=False, nullable=False),
    sa.Column('completed', sa.BOOLEAN(), autoincrement=False, nullable=False),
    sa.Column('task_id', sa.INTEGER(), autoincrement=False, nullable=False),
    sa.ForeignKeyConstraint(['task_id'], ['tasks.id'], name=op.f('subtasks_task_id_fkey')),
    sa.PrimaryKeyConstraint('id', name=op.f('subtasks_pkey'))
    )
    op.drop_table('subtickets')
    op.drop_table('tickets')
    op.drop_table('roles')
    op.drop_table('organizations')
    # ### end Alembic commands ###
