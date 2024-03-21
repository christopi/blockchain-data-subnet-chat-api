"""models

Revision ID: c3382ec883cb
Revises: 
Create Date: 2024-04-09 09:48:59.479777

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c3382ec883cb'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('users',
    sa.Column('id', sa.UUID(), server_default=sa.text('gen_random_uuid()'), nullable=False),
    sa.Column('name', sa.String(), nullable=True),
    sa.Column('email', sa.String(), nullable=True),
    sa.Column('password', sa.String(), nullable=True),
    sa.Column('refresh_token', sa.String(), nullable=True),
    sa.Column('reset_token', sa.String(), nullable=True),
    sa.Column('source', sa.String(), nullable=True),
    sa.PrimaryKeyConstraint('id', name=op.f('pk__users'))
    )
    op.create_index(op.f('ix__users__email'), 'users', ['email'], unique=True)
    op.create_index(op.f('ix__users__id'), 'users', ['id'], unique=False)
    op.create_index(op.f('ix__users__name'), 'users', ['name'], unique=True)
    op.create_table('validators',
    sa.Column('id', sa.UUID(), server_default=sa.text('gen_random_uuid()'), nullable=False),
    sa.Column('uid', sa.Integer(), nullable=True),
    sa.Column('name', sa.String(), nullable=True),
    sa.PrimaryKeyConstraint('id', name=op.f('pk__validators')),
    sa.UniqueConstraint('uid', name=op.f('uq__validators__uid'))
    )
    op.create_index(op.f('ix__validators__id'), 'validators', ['id'], unique=False)
    op.create_index(op.f('ix__validators__name'), 'validators', ['name'], unique=True)
    op.create_table('chats',
    sa.Column('id', sa.UUID(), server_default=sa.text('gen_random_uuid()'), nullable=False),
    sa.Column('name', sa.String(), nullable=True),
    sa.Column('is_deleted', sa.Boolean(), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=True),
    sa.Column('updated_at', sa.DateTime(), nullable=True),
    sa.Column('user_id', sa.UUID(), nullable=True),
    sa.Column('validator_id', sa.UUID(), nullable=True),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], name=op.f('fk__chats__user_id__users')),
    sa.ForeignKeyConstraint(['validator_id'], ['validators.id'], name=op.f('fk__chats__validator_id__validators')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk__chats'))
    )
    op.create_index(op.f('ix__chats__id'), 'chats', ['id'], unique=False)
    op.create_table('messages',
    sa.Column('id', sa.UUID(), server_default=sa.text('gen_random_uuid()'), nullable=False),
    sa.Column('chat_id', sa.UUID(), nullable=True),
    sa.Column('content', sa.String(), nullable=True),
    sa.Column('is_deleted', sa.Boolean(), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=True),
    sa.Column('updated_at', sa.DateTime(), nullable=True),
    sa.ForeignKeyConstraint(['chat_id'], ['chats.id'], name=op.f('fk__messages__chat_id__chats')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk__messages'))
    )
    op.create_index(op.f('ix__messages__id'), 'messages', ['id'], unique=False)
    op.create_table('message_variations',
    sa.Column('id', sa.UUID(), server_default=sa.text('gen_random_uuid()'), nullable=False),
    sa.Column('message_id', sa.UUID(), nullable=True),
    sa.Column('validator_id', sa.UUID(), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=True),
    sa.Column('content', sa.String(), nullable=True),
    sa.Column('miner', sa.UUID(), nullable=True),
    sa.ForeignKeyConstraint(['message_id'], ['messages.id'], name=op.f('fk__message_variations__message_id__messages')),
    sa.ForeignKeyConstraint(['validator_id'], ['validators.id'], name=op.f('fk__message_variations__validator_id__validators')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk__message_variations'))
    )
    op.create_index(op.f('ix__message_variations__id'), 'message_variations', ['id'], unique=False)
    op.create_index(op.f('ix__message_variations__miner'), 'message_variations', ['miner'], unique=False)
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_index(op.f('ix__message_variations__miner'), table_name='message_variations')
    op.drop_index(op.f('ix__message_variations__id'), table_name='message_variations')
    op.drop_table('message_variations')
    op.drop_index(op.f('ix__messages__id'), table_name='messages')
    op.drop_table('messages')
    op.drop_index(op.f('ix__chats__id'), table_name='chats')
    op.drop_table('chats')
    op.drop_index(op.f('ix__validators__name'), table_name='validators')
    op.drop_index(op.f('ix__validators__id'), table_name='validators')
    op.drop_table('validators')
    op.drop_index(op.f('ix__users__name'), table_name='users')
    op.drop_index(op.f('ix__users__id'), table_name='users')
    op.drop_index(op.f('ix__users__email'), table_name='users')
    op.drop_table('users')
    # ### end Alembic commands ###
