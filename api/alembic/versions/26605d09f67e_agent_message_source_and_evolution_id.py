"""agent message source and evolution id

Revision ID: 26605d09f67e
Revises: d4a38c7cc38d
Create Date: 2026-09-03 18:40:07.503186

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '26605d09f67e'
down_revision: Union[str, None] = 'd4a38c7cc38d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # server_default aqui só pra backfill das linhas existentes (a tabela
    # já tem dados reais) — o default "web" de verdade fica só no lado do
    # ORM (models.py), igual o resto do projeto.
    op.add_column('agent_messages', sa.Column('source', sa.String(length=20), nullable=False, server_default='web'))
    op.alter_column('agent_messages', 'source', server_default=None)
    op.add_column('agent_messages', sa.Column('evolution_message_id', sa.String(length=100), nullable=True))
    op.create_unique_constraint('uq_agent_messages_evolution_message_id', 'agent_messages', ['evolution_message_id'])


def downgrade() -> None:
    op.drop_constraint('uq_agent_messages_evolution_message_id', 'agent_messages', type_='unique')
    op.drop_column('agent_messages', 'evolution_message_id')
    op.drop_column('agent_messages', 'source')
