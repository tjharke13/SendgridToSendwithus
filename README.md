# SendgridToSendwithus
Python script to handle conversion of SendGrid templates to Sendwithus templates

I came across the task of we were moving all of our email templating from SendGrid to Sendwithus and needed a easy way to handle this migration.  I didn't find anything that had the integration between SendGrid and Sendwithus in terms of managing templates, so I created this.  A few things in this is specific to my use case, but can be edited/extended to fit your needs.

My scenario

SendGrid contained about 100 email templates that needed to be moved over.  In SendGrid there was a different template for each language.  For example a template name would be "My First Email En Us".  With "En Us" denoting that it was the English - US template.  On the Sendwithus side I wanted to organize these templates to be under the same template, but have different locales.  So we would have one template name "My First Email", but will have many locales underneath.  So, this iis probably the most specific change that I have in this script.  The other parts of updating substitutions to follow Sendwithus format should be common for everyone. 
