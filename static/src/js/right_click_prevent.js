/** @odoo-module **/

import { prettifyMessageContent } from "@mail/utils/common/format" ;

import { ThreadService } from "@mail/core/common/thread_service";
import { patch } from "@web/core/utils/patch";

/** @type {import("@mail/core/common/thread_service").ThreadService} */
const threadServicePatch1 = {
    async getMessagePostParams({
        attachments,
        body,
        cannedResponseIds,
        isNote,
        mentionedChannels,
        mentionedPartners,
        thread,
    }) {
        const subtype = isNote ? "mail.mt_note" : "mail.mt_comment";
        const validMentions = this.store.user
            ? this.messageService.getMentionsFromText(body, {
                  mentionedChannels,
                  mentionedPartners,
              })
            : undefined;
        const partner_ids = validMentions?.partners.map((partner) => partner.id);
        const recipientEmails = [];
        const recipientAdditionalValues = {};
        if (!isNote) {
            const recipientIds = thread.suggestedRecipients
                .filter((recipient) => recipient.persona && recipient.checked)
                .map((recipient) => recipient.persona.id);
            thread.suggestedRecipients
                .filter((recipient) => recipient.checked && !recipient.persona)
                .forEach((recipient) => {
                    recipientEmails.push(recipient.email);
                    recipientAdditionalValues[recipient.email] = recipient.defaultCreateValues;
                });
            partner_ids?.push(...recipientIds);
        }
        let string_data = await prettifyMessageContent(body, validMentions)
        let body_html = $.parseHTML(string_data);
        for (const data of body_html) { 
            const $element = $(data); 
            if ($element.is('a.o_mail_redirect')) {
                let href = $element.attr('href'); 
                if (href) {
                    href = href.replace('&','&amp;')
                    string_data = string_data.replace(href, '#');
                }
            }
        }
        return {
            context: {
                mail_post_autofollow: !isNote && thread.hasWriteAccess,
            },
            post_data: {
                body: string_data,
                attachment_ids: attachments.map(({ id }) => id),
                attachment_tokens: attachments.map((attachment) => attachment.accessToken),
                canned_response_ids: cannedResponseIds,
                message_type: "comment",
                partner_ids,
                subtype_xmlid: subtype,
                partner_emails: recipientEmails,
                partner_additional_values: recipientAdditionalValues,
            },
            thread_id: thread.id,
            thread_model: thread.model,
        };
    }
};

patch(ThreadService.prototype, threadServicePatch1);
